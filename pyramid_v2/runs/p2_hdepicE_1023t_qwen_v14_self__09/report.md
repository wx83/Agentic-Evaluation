# pyramid2 run `p2_hdepicE_1023t_qwen_v14_self__09`

dataset hdepic_e · videos 1 · examiner `qwen3-omni-30b-a3b-instruct` · solver `qwen3-omni-30b-a3b-instruct` · n_per_layer 200 · seed 1023 · prompt physical-mental-draft2-hdepic-e+v8stair+v10l3ext+v11spatial+v12ego-gaze-ground

**结果为 provisional**:gold = Examiner 的 proposed_reference_answer,未经人工核验;open/plan 题由 Gemini judge 判。

## 每层概览

| layer | stop | turns | scored | correct | raw acc | cluster-dedup acc | follow-up | invalid/unresolved | confirmation |
|---|---|---|---|---|---|---|---|---|---|
| L1 | STAIRCASE_COMPLETE | 26 | 8 | 6 | 0.75 | 0.75 | 0 | 18/0 | - |
| L2 | STAIRCASE_COMPLETE | 34 | 13 | 5 | 0.385 | 0.385 | 0 | 21/0 | - |
| L3 | STAIRCASE_COMPLETE | 32 | 5 | 2 | 0.4 | 0.4 | 0 | 27/0 | - |
| L4 | STAIRCASE_COMPLETE | 3 | 0 | 0 | None | None | 0 | 3/0 | - |

## 每层 × skill 诊断结论

| layer | skill | verdict | scored | correct | clusters | first-try correct | supported hypotheses | confirmation |
|---|---|---|---|---|---|---|---|---|
| L1 | spatial_near | not_started | 0 | 0 | 0 |  | - | - |
| L1 | spatial_side | boundary 1.5 | 2 | 0 | 2 |  | - | - |
| L1 | object_recognition | boundary 2 | 4 | 4 | 4 |  | - | - |
| L1 | object_location_at_time | boundary 2 | 2 | 2 | 2 |  | - | - |
| L1 | object_grounding | not_started | 0 | 0 | 0 |  | - | - |
| L2 | sound_action_binding | boundary 3 | 1 | 1 | 1 |  | - | - |
| L2 | object_state_change | boundary<1 | 3 | 0 | 3 |  | - | - |
| L2 | action_temporal_order | boundary 4 | 1 | 0 | 1 |  | - | - |
| L2 | action_recognition | boundary<1 | 4 | 1 | 4 |  | - | - |
| L2 | event_object_role | boundary 2.5 | 4 | 3 | 4 |  | - | - |
| L2 | sound_anchored_spatial_near | not_started | 0 | 0 | 0 |  | - | - |
| L2 | sound_anchored_spatial_side | not_started | 0 | 0 | 0 |  | - | - |
| L2 | sound_movement_binding | not_started | 0 | 0 | 0 |  | - | - |
| L3 | inter_event_temporal_reasoning | not_started | 0 | 0 | 0 |  | - | - |
| L3 | inter_event_spatial_extreme | boundary 2 | 2 | 1 | 2 |  | - | - |
| L3 | inter_event_spatial_order | not_started | 0 | 0 | 0 |  | - | - |
| L3 | cross_event_integration | not_started | 0 | 0 | 0 |  | - | - |
| L3 | hidden_state_inference | boundary<1 | 2 | 0 | 2 |  | - | - |
| L3 | spatial_state_integration | not_started | 0 | 0 | 0 |  | - | - |
| L3 | causal_prerequisite_reasoning | boundary 2.0 | 1 | 1 | 1 |  | - | - |
| L3 | egocentric_frame_transform | not_started | 0 | 0 | 0 |  | - | - |
| L3 | gaze_primed_next_pickup | not_started | 0 | 0 | 0 |  | - | - |
| L4 | goal_conditioned_planning | not_started | 0 | 0 | 0 |  | - | - |
| L4 | plan_gap_filling | not_started | 0 | 0 | 0 |  | - | - |

## L1 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | spatial_near | single_choice | coverage | - | item_invalid | None | A | At the moment the spatula is tapped on the side of the pan, which object is nearest to the spatula? |
| 2 | DIAG | spatial_near | single_choice | coverage | - | item_invalid | None | A | At the end of the clip, which object is nearest to the pan? |
| 3 | DIAG | spatial_near | single_choice | coverage | - | item_invalid | None | B | At the end of the clip, which object is nearest to the tea towel? |
| 4 | DIAG | spatial_side | single_choice | coverage | - | item_invalid | None | A | At the moment the pan is tapped on the side of the hob, which of the following objects is farthest to the righ |
| 5 | DIAG | spatial_side | single_choice | coverage | - | wrong | D | C | At the moment the pan is tapped on the side of the hob, which of the following objects is farthest to the righ |
| 6 | DIAG | spatial_side | single_choice | coverage | - | wrong | None | C | At the moment the pepper grinder is being twisted to add pepper to the vegetables, which of the following obje |
| 7 | DIAG | spatial_side | single_choice | coverage | - | item_invalid | None | D | At the moment the sound of water is heard, which of the following objects is farthest to the left from the cam |
| 8 | DIAG | spatial_side | single_choice | coverage | - | item_invalid | None | C | At the moment the pan is tapped on the side of the hob, which of the following objects is farthest to the righ |
| 9 | DIAG | spatial_side | single_choice | coverage | - | item_invalid | None | A | At the moment the sound of stirring is heard, which of the following objects is farthest to the right from the |
| 10 | DIAG | object_recognition | single_choice | coverage | - | correct | B | B | According to the sub-goal for step 3, what ingredient is being chopped in steps 1 and 2? |
| 11 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | According to the sub-goal for step 6, what object is being stirred in the pan? |
| 12 | DIAG | object_recognition | single_choice | coverage | - | correct | B | B | According to the sub-goal for step 1, what ingredient is being chopped in steps 1 and 2? |
| 13 | DIAG | object_recognition | single_choice | coverage | - | correct | B | B | According to the sub-goal for step 1, what ingredient is being chopped in steps 1 and 2? |
| 14 | DIAG | object_recognition | single_choice | coverage | - | item_invalid | None | C | According to the sub-goal for step 4, what object is being stirred in the pan? |
| 15 | DIAG | object_recognition | single_choice | coverage | - | item_invalid | None | B | According to the narration, what object is used to mix the vegetables in the pan? |
| 16 | DIAG | object_recognition | single_choice | coverage | - | item_invalid | None | C | According to the sub-goal for step 7, what object is being stirred in the pan? |
| 17 | DIAG | object_location_at_time | single_choice | coverage | - | item_invalid | None | A | At the moment the spatula is tapped on the side of the pan, which object is nearest to the spatula? |
| 18 | DIAG | object_location_at_time | single_choice | coverage | - | item_invalid | None | A | At the moment the spatula is tapped on the side of the pan, which object is nearest to the spatula? |
| 19 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | At the moment the tea towel is moved from the counter to the sink, which object is located to the left of the  |
| 20 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | At the moment the pan is tapped on the side of the hob, which object is nearest to the pan? |
| 21 | DIAG | object_location_at_time | multi_select | coverage | - | item_invalid | None | B | At the moment the pan is tapped on the side of the hob, which of the following objects is farthest to the righ |
| 22 | DIAG | object_location_at_time | single_choice | coverage | - | item_invalid | None | B | At the moment the pan is tapped on the side of the hob, which object is nearest to the pan? |
| 23 | DIAG | object_location_at_time | single_choice | coverage | - | item_invalid | None | A | At the moment the spatula is tapped on the side of the pan, which object is nearest to the spatula? |
| 24 | DIAG | object_grounding | bbox | coverage | - | item_invalid | None | 15.0, 60.7, 63.2, 87.2 | What is the bounding box of the pan in the first frame of step 4? |
| 25 | DIAG | object_grounding | bbox | coverage | - | item_invalid | None | 22.9, 63.1, 70.3, 89.7 | What is the bounding box of the pan in the first frame of the clip? |
| 26 | DIAG | object_grounding | bbox | coverage | - | item_invalid | None | 23.6, 63.2, 69.9, 89.7 | What is the bounding box of the pan in the first frame of the clip? |

## L2 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | sound_action_binding | multi_select | coverage | - | correct | B | B | Which of the following sounds are produced during the action of chopping broccoli? |
| 2 | DIAG | sound_action_binding | multi_select | coverage | - | item_invalid | None | A | Which of the following actions is most likely to have produced the sound of metal-only collision heard at 1592 |
| 3 | DIAG | sound_action_binding | multi_select | coverage | - | item_invalid | None | B | Which of the following sounds are produced during the action of stirring the vegetables in the pan? |
| 4 | DIAG | sound_action_binding | multi_select | coverage | - | item_invalid | None | B | Which of the following sounds are produced during the action of chopping broccoli? |
| 5 | DIAG | object_state_change | single_choice | coverage | - | item_invalid | None | A | After the action of putting the pan under the running water to clean off the soap, where are the vegetables? |
| 6 | DIAG | object_state_change | single_choice | coverage | - | item_invalid | None | B | After the action of stirring the vegetables in the pan is completed, where are the vegetables? |
| 7 | DIAG | object_state_change | single_choice | coverage | - | wrong | A | B | According to the narration, where was the broccoli before the action of chopping it into smaller pieces began? |
| 8 | DIAG | object_state_change | single_choice | coverage | - | wrong | A | B | According to the narration, what happens to the spatula after the vegetables are mixed in the pan? |
| 9 | DIAG | object_state_change | single_choice | coverage | - | wrong | B | A | According to the narration, what happens to the spatula after the vegetables are mixed in the pan? |
| 10 | DIAG | action_temporal_order | short_answer | coverage | - | wrong | grab the broccoli from the air | grab the broccoli from the air | According to the narration, what is the correct order of the following actions: 'scrape the broccoli to the si |
| 11 | DIAG | action_temporal_order | short_answer | coverage | - | item_invalid | None | With the tongs, grab another p | According to the narration, what is the correct order of the following actions: 'Hold the broccoli steady with |
| 12 | DIAG | action_temporal_order | short_answer | coverage | - | item_invalid | None | With my right hand, pick up th | According to the narration, what is the correct order of the following actions: 'With my left hand, pick up th |
| 13 | DIAG | action_temporal_order | short_answer | coverage | - | item_invalid | None | With my left hand, shake the p | According to the narration, what is the correct order of the following actions: 'With my left hand, shake the  |
| 14 | DIAG | action_recognition | single_choice | coverage | - | wrong | A | B | According to the narration, what is the action performed in steps 1 and 2 of the recipe? |
| 15 | DIAG | action_recognition | single_choice | coverage | - | item_invalid | None | B | According to the narration, what is the action performed in step 7 of the recipe? |
| 16 | DIAG | action_recognition | single_choice | coverage | - | wrong | C | B | According to the narration, what is the action performed in step 5 of the recipe? |
| 17 | DIAG | action_recognition | single_choice | coverage | - | correct | B | B | According to the narration, what is the action being performed in the clip? |
| 18 | DIAG | action_recognition | single_choice | coverage | - | wrong | C | B | According to the narration, what is the action being performed in the clip? |
| 19 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | According to the narration, what is the object being used to stir the vegetables in the pan? |
| 20 | DIAG | event_object_role | single_choice | coverage | - | item_invalid | None | A | According to the narration, what is the object being used to stir the vegetables in the pan? |
| 21 | DIAG | event_object_role | single_choice | coverage | - | wrong | C | B | According to the narration, what is the object being used to turn on the kitchen tap? |
| 22 | DIAG | event_object_role | single_choice | coverage | - | item_invalid | None | B | According to the narration, what is the object being used to stir the vegetables in the pan? |
| 23 | DIAG | event_object_role | single_choice | coverage | - | correct | B | B | According to the narration, what is the object being used to move the broccoli from the cutting board into the |
| 24 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | According to the narration, what is the object being used to hold the baking tray steady? |
| 25 | DIAG | event_object_role | single_choice | coverage | - | item_invalid | None | B | According to the narration, what ingredient is being chopped in steps 1 and 2? |
| 26 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | item_invalid | None | B | According to the audio and video, which object is closest to the sound of stirring? |
| 27 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | item_invalid | None | A | According to the audio and video, which object is closest to the sound of stirring? |
| 28 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | item_invalid | None | A | According to the audio and video, which object is closest to the sound of stirring? |
| 29 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | item_invalid | None | D | According to the audio and video, which object is located to the left of the sound of the metal-only collision |
| 30 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | item_invalid | None | A | According to the audio and video, which object is located to the right of the sound of the metal-only collisio |
| 31 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | item_invalid | None | A | According to the audio and video, which object is located to the right of the sound of stirring? |
| 32 | DIAG | sound_movement_binding | single_choice | coverage | - | item_invalid | None | B | According to the audio and video, what object is being stirred in the pan? |
| 33 | DIAG | sound_movement_binding | single_choice | coverage | - | item_invalid | None | B | According to the audio and video, what object is being stirred in the pan? |
| 34 | DIAG | sound_movement_binding | single_choice | coverage | - | item_invalid | None | D | According to the audio and video, what object is being stirred in the pan? |

## L3 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | inter_event_temporal_reasoning | single_choice | coverage | - | item_invalid | None | A | According to the task plan, which step must be completed before transferring the chopped broccoli and other ve |
| 2 | DIAG | inter_event_temporal_reasoning | single_choice | coverage | - | item_invalid | None | C | According to the task plan, which step must be completed before transferring the chopped broccoli and other ve |
| 3 | DIAG | inter_event_temporal_reasoning | short_answer | coverage | - | item_invalid | None | Chop the broccoli into smaller | According to the task plan, which step must be completed before transferring the chopped broccoli and other ve |
| 4 | DIAG | inter_event_spatial_extreme | single_choice | coverage | - | item_invalid | None | A | According to the task plan, which step must be completed before transferring the chopped broccoli and other ve |
| 5 | DIAG | inter_event_spatial_extreme | single_choice | coverage | - | correct | A | A | At the end of the clip, which of the following objects is farthest from the tea towel? |
| 6 | DIAG | inter_event_spatial_extreme | single_choice | coverage | - | wrong | D | A | At the end of the clip, which of the following objects is farthest from the tea towel? |
| 7 | DIAG | inter_event_spatial_extreme | single_choice | coverage | - | item_invalid | None | C | At the end of the clip, which of the following objects is farthest from the pan? |
| 8 | DIAG | inter_event_spatial_extreme | single_choice | coverage | - | item_invalid | None | C | At the end of the clip, which of the following objects is farthest from the pan? |
| 9 | DIAG | inter_event_spatial_extreme | single_choice | coverage | - | item_invalid | None | A | At the end of the clip, which of the following objects is farthest from the pan? |
| 10 | DIAG | inter_event_spatial_order | single_choice | coverage | - | item_invalid | None | D | According to the spatial relations at the end of the clip, which of the following correctly orders the objects |
| 11 | DIAG | inter_event_spatial_order | single_choice | coverage | - | item_invalid | None | C | According to the spatial relations at the end of the clip, which of the following correctly orders the knife,  |
| 12 | DIAG | inter_event_spatial_order | single_choice | coverage | - | item_invalid | None | A | According to the spatial relations at the end of the clip, which of the following correctly orders the glass,  |
| 13 | DIAG | cross_event_integration | single_choice | coverage | - | item_invalid | None | A | According to the task plan, what ingredient is carried over from the step of chopping broccoli to the step of  |
| 14 | DIAG | cross_event_integration | single_choice | coverage | - | item_invalid | None | A | According to the task plan, what ingredient is carried over from the step of chopping broccoli to the step of  |
| 15 | DIAG | cross_event_integration | single_choice | coverage | - | item_invalid | None | A | According to the task plan, what ingredient is carried over from the step of chopping broccoli to the step of  |
| 16 | DIAG | hidden_state_inference | single_choice | coverage | - | item_invalid | None | B | At the end of the clip, what is the state of the tap? |
| 17 | DIAG | hidden_state_inference | single_choice | coverage | - | item_invalid | None | A | According to the task plan, what is the state of the hob at the end of step 6? |
| 18 | DIAG | hidden_state_inference | single_choice | coverage | - | wrong | D | A | At the end of the clip, what is the state of the air fryer? |
| 19 | DIAG | hidden_state_inference | single_choice | coverage | - | wrong | C | B | At the end of the clip, what is the state of the trash can? |
| 20 | DIAG | spatial_state_integration | single_choice | coverage | - | item_invalid | None | B | At the end of the clip, which of the following objects is farthest from the tea towel? |
| 21 | DIAG | spatial_state_integration | single_choice | coverage | - | item_invalid | None | A | At the end of the clip, which of the following objects is farthest from the pan? |
| 22 | DIAG | spatial_state_integration | single_choice | coverage | - | item_invalid | None | D | At the end of the clip, which of the following objects is farthest from the bottle of sesame oil? |
| 23 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | item_invalid | None | C | According to the task plan, which of the following steps is a prerequisite for stirring the vegetables in the  |
| 24 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | C | C | According to the task plan, which of the following steps is a prerequisite for stirring the vegetables in the  |
| 25 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | item_invalid | None | C | According to the task plan, which of the following steps is a prerequisite for stirring the vegetables in the  |
| 26 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | item_invalid | None | C | According to the task plan, which of the following steps is a prerequisite for stirring the vegetables in the  |
| 27 | DIAG | egocentric_frame_transform | single_choice | coverage | - | item_invalid | None | A | At the end of the clip, from the camera wearer's own viewpoint as the camera faces, where is the baking tray? |
| 28 | DIAG | egocentric_frame_transform | single_choice | coverage | - | item_invalid | None | D | At the end of the clip, from the camera wearer's own viewpoint as the camera faces, where is the spoon? |
| 29 | DIAG | egocentric_frame_transform | single_choice | coverage | - | item_invalid | None | D | At the end of the clip, from the camera wearer's own viewpoint as the camera faces, where is the sponge? |
| 30 | DIAG | gaze_primed_next_pickup | single_choice | coverage | - | item_invalid | None | A | According to the task plan, which object is the wearer about to pick up next? |
| 31 | DIAG | gaze_primed_next_pickup | single_choice | coverage | - | item_invalid | None | A | According to the task plan, which object is the wearer about to pick up next? |
| 32 | DIAG | gaze_primed_next_pickup | single_choice | coverage | - | item_invalid | None | A | According to the task plan, which object is the wearer about to pick up next? |

## L4 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | goal_conditioned_planning | single_choice | coverage | - | item_invalid | None | D | The task is to add broccoli and green beans to a pan and stir. The current step is 'Finish stirring the vegeta |
| 2 | DIAG | goal_conditioned_planning | single_choice | coverage | - | item_invalid | None | D | The task is to add broccoli and green beans to a pan and stir. The current step is 'Finish stirring the vegeta |
| 3 | DIAG | goal_conditioned_planning | single_choice | coverage | - | item_invalid | None | A | The task is to add broccoli and green beans to a pan and stir. The current step is 'Transfer the chopped brocc |

## Gemini 用量

| role | calls | errors | tok_in | tok_out | tok_think |
|---|---|---|---|---|---|
| examiner | 250 | 0 | 9862836 | 0 | 0 |
| judge | 1 | 0 | 369 | 68 | 200 |
| scope | 3 | 0 | 13347 | 0 | 0 |
| solver | 26 | 0 | 132115 | 0 | 0 |
