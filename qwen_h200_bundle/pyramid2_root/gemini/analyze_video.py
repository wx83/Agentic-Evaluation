import argparse
import json
import time
from pathlib import Path
from typing import Literal

from google import genai
from pydantic import BaseModel, Field


# ---------- Pass 1 output ----------

class CandidateMilestone(BaseModel):
    order: int
    label: str
    goal_state: str
    why_necessary: str


class TaskPlan(BaseModel):
    high_level_task: str
    task_summary: str
    milestones: list[CandidateMilestone]


# ---------- Final annotation output ----------

class Evidence(BaseModel):
    modality: Literal[
        "visual",
        "audio",
        "speech",
        "spatial",
        "motion"
    ]
    timestamp_s: float
    description: str


class Milestone(BaseModel):
    id: str
    order: int
    label: str

    start_s: float
    end_s: float

    dependency_ids: list[str]

    # State that must become true
    goal_state: str

    # Observable predicates for automated evaluation
    completion_criteria: list[str]

    # Conditions distinguishing failure from completion
    failure_criteria: list[str]

    # Question that can later be given to an omni evaluator
    evaluator_question: str

    evidence: list[Evidence]

    reference_status: Literal[
        "completed",
        "not_completed",
        "uncertain"
    ]

    confidence: float = Field(ge=0.0, le=1.0)
    review_note: str


class TaskAnnotation(BaseModel):
    video_name: str
    high_level_task: str
    task_summary: str

    milestones: list[Milestone]

    annotation_confidence: float = Field(ge=0.0, le=1.0)
    needs_human_review: bool
    review_reasons: list[str]


def wait_for_video(client, video_path: Path):
    uploaded = client.files.upload(file=str(video_path))

    while not uploaded.state or uploaded.state.name == "PROCESSING":
        print("Gemini is processing the video...")
        time.sleep(5)
        uploaded = client.files.get(name=uploaded.name)

    if uploaded.state.name != "ACTIVE":
        raise RuntimeError(
            f"Video processing failed: {uploaded.state.name}"
        )

    return uploaded


def generate_plan(client, uploaded, known_task: str | None, model: str):
    task_context = (
        f"The known task instruction is: {known_task}"
        if known_task
        else
        "No task instruction is provided. Infer the high-level task."
    )

    prompt = f"""
You are annotating an egocentric audiovisual trajectory for a
long-horizon task benchmark.

{task_context}

First determine the principal task demonstrated in the video. Then
decompose it into 3 to 10 ordered semantic milestones.

Milestone requirements:

1. A milestone must represent an observable and meaningful state
   transition, not an arbitrary time interval.
2. Do not use low-level body motions such as "walk forward",
   "move the hand", or "look left", unless that motion itself is the goal.
3. Prefer route-invariant states. For example, use "the wearer has
   entered the kitchen", not "the wearer turns left at the chair".
4. Each milestone should be independently judgeable using video,
   audio, or another observable sensor stream.
5. Milestones should collectively explain completion of the main task.
6. Do not invent objects, locations, sounds, or events that are not
   supported by the video.
7. Separate navigation, localization, interaction, and final task
   completion when these are genuinely distinct stages.
8. Audio should be considered when it identifies an event, speaker,
   target, direction, or state that visual evidence alone cannot establish.
"""

    response = client.interactions.create(
        model=model,
        input=[
            {
                "type": "video",
                "uri": uploaded.uri,
                "mime_type": uploaded.mime_type,
            },
            {"type": "text", "text": prompt},
        ],
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": TaskPlan.model_json_schema(),
        },
    )

    return TaskPlan.model_validate_json(response.output_text)


def align_plan(client, uploaded, plan: TaskPlan, model: str):
    plan_json = json.dumps(plan.model_dump(), indent=2)

    prompt = f"""
You are producing the final temporal annotation for an egocentric
audiovisual task trajectory.

A first-pass annotator proposed this task decomposition:

{plan_json}

Re-examine the complete video and produce the final annotation.

Rules:

1. Correct, merge, split, or remove candidate milestones when the video
   evidence requires it.
2. The start time is when purposeful execution of that milestone begins.
3. The end time is the earliest moment when its goal state is observably
   achieved.
4. Timestamps are seconds from the beginning of the video.
5. Completion criteria must be observable predicates, not intentions.
6. Criteria must be usable on a different generated trajectory. Avoid
   details unique to this particular person's motion or exact route.
7. An evaluator question must be answerable with:
   achieved, not achieved, or insufficient evidence.
8. Include evidence timestamps and state what can actually be observed.
9. Use audio evidence only when the relevant sound or speech is audible.
10. Do not assume a milestone succeeded merely because the later task
    appears successful.
11. Set reference_status to uncertain when the available evidence is
    insufficient.
12. Add a human-review reason for ambiguous boundaries, occlusion,
    unclear audio, uncertain spatial location, or alternative valid paths.
"""

    response = client.interactions.create(
        model=model,
        input=[
            {
                "type": "video",
                "uri": uploaded.uri,
                "mime_type": uploaded.mime_type,
            },
            {"type": "text", "text": prompt},
        ],
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": TaskAnnotation.model_json_schema(),
        },
    )

    return TaskAnnotation.model_validate_json(response.output_text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--task",
        default=None,
        help="Optional known high-level task instruction",
    )
    parser.add_argument(
        "--model",
        default="gemini-3.6-flash",
    )
    args = parser.parse_args()

    video_path = Path(args.video)
    output_path = Path(args.output)

    if not video_path.exists():
        raise FileNotFoundError(video_path)

    client = genai.Client()
    uploaded = wait_for_video(client, video_path)

    try:
        print("Pass 1: generating milestone plan...")
        plan = generate_plan(
            client,
            uploaded,
            known_task=args.task,
            model=args.model,
        )

        print("Pass 2: aligning milestones to video...")
        annotation = align_plan(
            client,
            uploaded,
            plan,
            model=args.model,
        )

        # Do not depend on Gemini to reproduce the filename correctly.
        annotation.video_name = video_path.name

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            annotation.model_dump_json(indent=2),
            encoding="utf-8",
        )

        print(f"Saved annotation to {output_path}")

    finally:
        # Remove the temporary Gemini upload after annotation.
        client.files.delete(name=uploaded.name)


if __name__ == "__main__":
    main()