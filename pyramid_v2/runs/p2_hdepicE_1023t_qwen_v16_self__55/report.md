# pyramid2 run `p2_hdepicE_1023t_qwen_v16_self__55`

dataset hdepic_e · videos 1 · examiner `qwen3-omni-30b-a3b-instruct` · solver `qwen3-omni-30b-a3b-instruct` · n_per_layer 200 · seed 1023 · prompt physical-mental-draft2-hdepic-e+v16sg

**结果为 provisional**:gold = Examiner 的 proposed_reference_answer,未经人工核验;open/plan 题由 Gemini judge 判。

## 每层概览

| layer | stop | turns | scored | correct | raw acc | cluster-dedup acc | follow-up | invalid/unresolved | confirmation |
|---|---|---|---|---|---|---|---|---|---|
| L1 | STAIRCASE_COMPLETE | 13 | 8 | 2 | 0.25 | 0.25 | 0 | 5/0 | - |
| L2 | STAIRCASE_COMPLETE | 40 | 20 | 13 | 0.65 | 0.611 | 0 | 20/0 | - |
| L3 | STAIRCASE_COMPLETE | 16 | 9 | 7 | 0.778 | 0.778 | 0 | 6/0 | - |
| L4 | STAIRCASE_COMPLETE | 7 | 2 | 1 | 0.5 | 0.5 | 0 | 5/0 | - |

## 每层 × skill 诊断结论

| layer | skill | verdict | scored | correct | clusters | first-try correct | supported hypotheses | confirmation |
|---|---|---|---|---|---|---|---|---|
| L1 | spatial_near | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L1 | spatial_side | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L1 | object_recognition | boundary<1 | 4 | 1 | 4 |  | - | - |
| L1 | object_location_at_time | boundary<1 | 4 | 1 | 4 |  | - | - |
| L1 | object_grounding | not_started | 0 | 0 | 0 |  | - | - |
| L2 | sound_action_binding | boundary<1 | 4 | 1 | 4 |  | - | - |
| L2 | object_state_change | not_started | 0 | 0 | 0 |  | - | - |
| L2 | action_temporal_order | boundary 3 | 4 | 4 | 4 |  | - | - |
| L2 | action_recognition | boundary 3 | 8 | 6 | 6 |  | - | - |
| L2 | event_object_role | boundary 2.5 | 3 | 2 | 3 |  | - | - |
| L2 | sound_anchored_spatial_near | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L2 | sound_anchored_spatial_side | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L2 | sound_movement_binding | boundary 2 | 1 | 0 | 1 |  | - | - |
| L3 | cross_event_integration | boundary 3.5 | 6 | 5 | 6 |  | - | - |
| L3 | hidden_state_inference | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | spatial_state_integration | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | causal_prerequisite_reasoning | boundary<1 | 3 | 2 | 3 |  | - | - |
| L4 | goal_conditioned_planning | boundary 1.5 | 2 | 1 | 2 |  | - | - |

## L1 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | object_recognition | single_choice | coverage | - | correct | B | B | About 8 seconds into the clip, the camera wearer is performing an action with a container. What is the object  |
| 2 | DIAG | object_recognition | single_choice | coverage | - | wrong | A | B | About 10 seconds into the clip, the camera wearer is using their left hand to place an object on a surface. Wh |
| 3 | DIAG | object_recognition | single_choice | coverage | - | wrong | C | A | About 4 seconds into the clip, the camera wearer is holding an object in their left hand. What is the object? |
| 4 | DIAG | object_recognition | single_choice | coverage | - | wrong | A | B | About 4 seconds into the clip, the camera wearer is performing an action with a container. What is the object  |
| 5 | DIAG | object_location_at_time | single_choice | coverage | - | correct | B | B | About 10 seconds into the clip, the camera wearer is rolling the chicken ball in the flour bowl. Where is the  |
| 6 | DIAG | object_location_at_time | single_choice | same_skill_new_event | - | item_invalid | None | C | About 6 seconds into the clip, the camera wearer places an object on the counter. Where is this object placed? |
| 7 | DIAG | object_location_at_time | single_choice | same_skill_new_event | - | wrong | A | C | About 6 seconds into the clip, the camera wearer places an object on the counter. Where is this object placed? |
| 8 | DIAG | object_location_at_time | single_choice | same_skill_new_event | - | item_invalid | None | B | About 6 seconds into the clip, the camera wearer places an object on the counter. Where is this object placed? |
| 9 | DIAG | object_location_at_time | single_choice | coverage | - | wrong | D | B | About 4 seconds into the clip, the camera wearer is dipping the chicken ball into the egg bowl. Where is the c |
| 10 | DIAG | object_location_at_time | single_choice | coverage | - | wrong | A | B | About 10 seconds into the clip, the camera wearer is rolling the second chicken ball in the flour bowl. Where  |
| 11 | DIAG | object_grounding | bbox | coverage | - | item_invalid | None | 51.3, 72.5, 57.8, 80.0 | In the first frame of the clip, what is the bounding box of the lid of the breadcrumb container? |
| 12 | DIAG | object_grounding | bbox | coverage | - | item_invalid | None | 51.3, 72.5, 57.8, 80.0 | In the first frame of the clip, what is the bounding box of the lid of the breadcrumb container? |
| 13 | DIAG | object_grounding | bbox | coverage | - | item_invalid | None | 41.9, 78.1, 48.9, 86.5 | In the first frame of the clip, what is the bounding box of the lid of the breadcrumb container? |

## L2 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | item_invalid | None | A | In the audio, a rustling sound is heard. What action is the camera wearer performing at the same time? |
| 2 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | correct | D | D | In the audio, a series of metallic and wooden clattering sounds are heard. What action is the camera wearer pe |
| 3 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | wrong | B | A | In the audio, a 'plastic-only collision' sound is heard. What action is the camera wearer performing at the sa |
| 4 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | wrong | D | C | In the audio, a 'metal / plastic collision' sound is heard. What action is the camera wearer performing at the |
| 5 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | wrong | C | D | In the audio, a 'metal / wood collision' sound is heard. What action is the camera wearer performing at the sa |
| 6 | DIAG | object_state_change | single_choice | same_skill_new_event | - | item_invalid | None | B | In the clip, the camera wearer places an empty bowl on the counter. What is the final location of the bowl aft |
| 7 | DIAG | object_state_change | single_choice | same_skill_new_event | - | item_invalid | None | A | In the clip, the camera wearer places an empty bowl on the counter. What is the final location of the bowl aft |
| 8 | DIAG | object_state_change | single_choice | same_skill_new_event | - | item_invalid | None | A | In the clip, the camera wearer shapes a mixture into a ball. What is the final state of the object they are ho |
| 9 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | item_invalid | None | A | In the clip, the camera wearer performs two actions. First, they pour breadcrumbs from a container into a bowl |
| 10 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | item_invalid | None | A | In the clip, the camera wearer performs two actions. First, they pour breadcrumbs from a container into a bowl |
| 11 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | A | A | In the clip, the camera wearer performs two actions. First, they pick up the container of breadcrumbs. Immedia |
| 12 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | item_invalid | None | A | In the clip, the camera wearer performs two actions. First, they retrieve flour from the cabinet. Immediately  |
| 13 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | A | A | In the clip, the camera wearer performs two actions. First, they retrieve flour from the cabinet. Immediately  |
| 14 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | item_invalid | None | A | In the clip, the camera wearer performs two actions. First, they roll the chicken ball in their hands to impro |
| 15 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | item_invalid | None | A | In the clip, the camera wearer performs two actions. First, they roll the chicken ball in their hands to impro |
| 16 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | A | A | In the clip, the camera wearer performs two actions. First, they dip a chicken ball into an egg bowl. Immediat |
| 17 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | A | A | In the clip, the camera wearer performs two actions. First, they pick up the uncoated potato chicken ball from |
| 18 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | item_invalid | None | A | In the clip, the camera wearer performs two actions. First, they dip the second chicken ball into the egg bowl |
| 19 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | item_invalid | None | A | In the clip, the camera wearer performs two actions. First, they sprinkle more flour onto the chicken ball. Im |
| 20 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | item_invalid | None | A | In the clip, the camera wearer performs two actions. First, they pour breadcrumbs from a container into a bowl |
| 21 | DIAG | action_recognition | single_choice | same_skill_new_event | - | item_invalid | None | A | In the clip, the camera wearer performs an action involving a container and a bowl. What is the specific actio |
| 22 | DIAG | action_recognition | single_choice | same_skill_new_event | - | item_invalid | None | A | In the clip, the camera wearer performs an action with a container and a bowl. What is the specific action bei |
| 23 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | C | C | In the clip, the camera wearer places an empty bowl on the counter. What is the specific action being performe |
| 24 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | In the clip, the camera wearer performs an action involving flour and a bowl. What is the specific action bein |
| 25 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | In the clip, the camera wearer performs an action involving a mixture and their hands. What is the specific ac |
| 26 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | B | B | In the clip, the camera wearer performs an action involving a chicken ball and a bowl of breadcrumbs. What is  |
| 27 | DIAG | action_recognition | short_answer | same_skill_new_event | - | wrong | Dipping the chicken ball in th | Picking up the uncoated potato | In the clip, the camera wearer picks up an uncoated potato chicken ball from the foil using their left hand, w |
| 28 | DIAG | action_recognition | single_choice | same_skill_new_event | - | wrong | D | B | In the clip, the camera wearer places the chicken ball in their left hand and then uses their right hand to sc |
| 29 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | In the clip, the camera wearer performs an action involving a mixture and their hands. What is the specific ac |
| 30 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | B | B | In the clip, the camera wearer performs an action involving a chicken ball and a bowl of egg. What is the spec |
| 31 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | C | C | In the action of pouring breadcrumbs into a bowl, what is the object being poured? |
| 32 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | C | C | In the action of placing the empty bowl on the counter, what is the object being placed? |
| 33 | DIAG | event_object_role | single_choice | same_skill_new_event | - | wrong | D | A | In the action of retrieving flour from the cabinet, what is the object being retrieved? |
| 34 | DIAG | event_object_role | single_choice | same_skill_new_event | - | item_invalid | None | C | In the action of rolling the chicken ball in the flour bowl, what is the object being rolled? |
| 35 | DIAG | event_object_role | single_choice | same_skill_new_event | - | item_invalid | None | C | In the action of rolling the chicken ball in the flour bowl, what is the object being rolled? |
| 36 | DIAG | event_object_role | single_choice | same_skill_new_event | - | item_invalid | None | C | In the action of rolling the egg-coated chicken ball in the bowl of breadcrumbs, what is the object being roll |
| 37 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | wrong | C | B | In the audio, a 'plastic-only collision' sound is heard. What action is the camera wearer performing at the sa |
| 38 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | item_invalid | None | A | In the audio, a 'kneading' sound is heard. What action is the camera wearer performing at the same time? |
| 39 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | item_invalid | None | D | In the audio, a 'metal / plastic collision' sound is heard. What action is the camera wearer performing at the |
| 40 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | item_invalid | None | B | In the audio, a 'metal / wood collision' sound is heard. What action is the camera wearer performing at the sa |

## L3 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | B | B | What was dispensed from the container before it was stored away? |
| 2 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | item_invalid | None | A | What was the coating on the chicken ball just before it was dipped in the egg? |
| 3 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | What was the state of the chicken ball just before it was dipped in the egg? |
| 4 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | What was the person doing with the chicken mixture after finishing the first breaded ball? |
| 5 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | What was the coating on the second chicken ball just before it was dipped in the egg? |
| 6 | DIAG | cross_event_integration | short_answer | same_skill_new_event | - | wrong | The bowl was empty. Time: 00:3 | The bowl was empty and placed  | What was the state of the bowl after the first sub-goal was completed? |
| 7 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | What was done to the bowl of breadcrumbs between the first and second sub-goals? |
| 8 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | item_invalid | None | D | What was the state of the flour bowl after the second sub-goal was completed? |
| 9 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | item_invalid | None | B | What was the state of the flour bowl after the second sub-goal was completed? |
| 10 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | item_invalid | None | A | What was the state of the chicken ball just before it was dipped in the egg? |
| 11 | DIAG | causal_prerequisite_reasoning | single_choice | same_skill_new_event | - | correct | A | A | Why was the empty bowl placed on the counter? |
| 12 | DIAG | causal_prerequisite_reasoning | single_choice | same_skill_new_event | - | wrong | B | A | What ingredient was added to the bowl before the chicken ball was rolled in it? |
| 13 | DIAG | causal_prerequisite_reasoning | single_choice | same_skill_new_event | - | item_invalid | None | C | Why was the bag of flour retrieved from the cabinet? |
| 14 | DIAG | causal_prerequisite_reasoning | single_choice | same_skill_new_event | - | correct | A | A | What was the purpose of placing the empty bowl on the counter in the previous step? |
| 15 | DIAG | causal_prerequisite_reasoning | - | - | - | env_failure | None | None |  |
| 16 | DIAG | causal_prerequisite_reasoning | single_choice | same_skill_new_event | - | item_invalid | None | A | What ingredient was added to the bowl before the chicken ball was rolled in it? |

## L4 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | goal_conditioned_planning | plan | same_skill_new_event | - | item_invalid | None | 1. Store the breadcrumbs conta | The task is to dredge each Chicken-cheese ball into flour, then dip into egg and roll in the breadcrumbs. The  |
| 2 | DIAG | goal_conditioned_planning | single_choice | same_skill_new_event | - | wrong | C | A | After setting up the breadcrumbs, the person must decide on the next step. Based on the actions observed in th |
| 3 | DIAG | goal_conditioned_planning | single_choice | same_skill_new_event | - | item_invalid | None | A | After placing the empty bowl, the person must decide to fetch the flour from the cabinet. Based on the actions |
| 4 | DIAG | goal_conditioned_planning | single_choice | same_skill_new_event | - | correct | A | A | After placing the empty bowl, the person must decide to fetch the flour from the cabinet. Based on the actions |
| 5 | DIAG | goal_conditioned_planning | single_choice | same_skill_new_event | - | item_invalid | None | A | The current sub-goal is to form the first chicken ball and coat it with flour. Based on the actions observed i |
| 6 | DIAG | goal_conditioned_planning | single_choice | same_skill_new_event | - | item_invalid | None | A | The current sub-goal is to form the first chicken ball and coat it with flour. Based on the actions observed i |
| 7 | DIAG | goal_conditioned_planning | single_choice | same_skill_new_event | - | item_invalid | None | C | The current sub-goal is to form the second chicken ball and coat it with flour. Based on the actions observed  |

## Gemini 用量

| role | calls | errors | tok_in | tok_out | tok_think |
|---|---|---|---|---|---|
| examiner | 76 | 0 | 1905123 | 0 | 0 |
| judge | 2 | 0 | 736 | 116 | 311 |
| solver | 39 | 0 | 258326 | 0 | 0 |
