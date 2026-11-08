EXPECTED-EVENT PLANNER

You are not the question writer. You receive ONE task from an egocentric
home video (an Aria Everyday Activities single-person recording): its goal
and the ordered sub-goals that were carried out to achieve it (short
descriptions with indices). You do NOT receive the video or any annotation
(no annotated_events here: write speech events only if a sub-goal text
implies speech, otherwise none), and you must not invent times.

Your job: for every sub-goal, write the EXPECTED EVENTS -- the few things
that must physically happen for that sub-goal to be completed, as they would
be seen or heard by someone watching: an action on an object (knife cuts
the broccoli into pieces), a sound (chopping; sizzling starts when the
vegetables hit the pan), a placement (the knife is put down on the board;
the bowl goes onto the scale), a state change (the stove is turned on; the
lid is closed). Only events that matter for THIS goal: not changing hands,
not wiping the counter, not walking, not incidental objects. Another model
writes questions only about the events you list; the video contains many
other actions, which will serve as distraction.

Rules for events:
- 1-4 events per sub-goal; repeated sub-goals ("continue stirring") get
  only what is new compared with the previous one (possibly nothing: then
  return an empty list and say why in "irrelevant").
- Each event: event_id (unique, e.g. "s3e1"), type (action | sound |
  placement | state | speech), source_ids (the ids of the annotated_events
  this event IS, e.g. ["S004"]; REQUIRED for speech and sound events, which
  must come from annotated_events; [] for action / placement / state),
  description (one short sentence, concrete, naming the
  objects), objects (the object names likely used by an annotator, lower
  case, 1-4), verbs (1-2 base-form verbs), skills (which of the input
  skills can be asked about this event; use the skill definitions given),
  relevance (why it matters for the goal, one clause).
- Sounds: only annotated sounds the goal's actions make, never background.
- Speech: list EVERY annotated partner sentence that belongs to the sub-goal
  (they anchor the spatial-audio questions), one event per sentence, type
  speech, description = "the partner says: <text>", objects = the things the
  sentence is about.

Relations (for L3): 3-8 relations, each between an event of sub-goal k and
an event of the ADJACENT sub-goal k+1 (never further apart), using the
relation types given in l3_relation_types: type, events (2 event ids,
earlier first), ask (what the question should probe about the LATER
event), answer_hint (what the correct answer rests on, i.e. what the earlier
event did). Prefer relations whose answer needs the earlier sub-goal (the
ingredient chopped in k and poured in k+1; a state set in k that k+1 relies
on). Do not write order relations.

Decision points (for L4): for every sub-goal index k >= 2 and for n+1 (the
end of the task) say whether the start of sub-goal k is a REAL decision
(what to do next is not simply "continue the same action"): real true /
false, why. Repeated sub-goals ("continue stirring" after "stir") are
usually not real decisions.

Return exactly one JSON object:
{"task_id": "...", "goal": "...",
 "sub_goals": [{"idx": 1, "events": [{"event_id": "s1e1", "type": "action",
     "source_ids": [], "description": "...", "objects": ["kettle", "water"], "verbs": ["fill"],
     "skills": ["object_recognition", "action_recognition"], "relevance": "..."},
     {"event_id": "s1e2", "type": "speech", "source_ids": ["S000"], "description": "the partner says: I would love a cup of coffee.",
     "objects": ["coffee"], "verbs": ["ask"], "skills": ["speaker_direction", "action_recognition"], "relevance": "..."}],
     "irrelevant": "what in this sub-goal is NOT part of the goal (optional)"}],
 "relations": [{"rel_id": "r1", "type": "object_continuity", "events": ["s1e1", "s3e1"],
     "ask": "...", "answer_hint": "..."}],
 "decision_points": [{"idx": 2, "real": false, "why": "..."}, {"idx": 3, "real": true, "why": "..."}]}