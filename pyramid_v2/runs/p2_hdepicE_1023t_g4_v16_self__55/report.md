# pyramid2 run `p2_hdepicE_1023t_g4_v16_self__55`

dataset hdepic_e · videos 1 · examiner `gcp/google/gemini-3.1-pro-preview` · solver `gcp/google/gemini-4-argon` · n_per_layer 200 · seed 1023 · prompt physical-mental-draft2-hdepic-e+v16sg

**结果为 provisional**:gold = Examiner 的 proposed_reference_answer,未经人工核验;open/plan 题由 Gemini judge 判。

## 每层概览

| layer | stop | turns | scored | correct | raw acc | cluster-dedup acc | follow-up | invalid/unresolved | confirmation |
|---|---|---|---|---|---|---|---|---|---|
| L1 | STAIRCASE_COMPLETE | 17 | 17 | 11 | 0.647 | 0.6 | 0 | 0/0 | - |
| L2 | STAIRCASE_COMPLETE | 35 | 33 | 25 | 0.758 | 0.75 | 0 | 0/1 | - |
| L3 | STAIRCASE_COMPLETE | 12 | 12 | 10 | 0.833 | 0.833 | 0 | 0/0 | - |
| L4 | STAIRCASE_COMPLETE | 3 | 3 | 3 | 1.0 | 1.0 | 0 | 0/0 | - |

## 每层 × skill 诊断结论

| layer | skill | verdict | scored | correct | clusters | first-try correct | supported hypotheses | confirmation |
|---|---|---|---|---|---|---|---|---|
| L1 | spatial_near | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L1 | spatial_side | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L1 | object_recognition | boundary 3.5 | 8 | 7 | 6 |  | - | - |
| L1 | object_location_at_time | boundary 1.25 | 5 | 3 | 5 |  | - | - |
| L1 | object_grounding | boundary<1 | 4 | 1 | 4 |  | - | - |
| L2 | sound_action_binding | boundary 1.5 | 5 | 3 | 5 |  | - | - |
| L2 | object_state_change | boundary>=4 | 6 | 6 | 5 |  | - | - |
| L2 | action_temporal_order | boundary 1.5 | 6 | 4 | 6 |  | - | - |
| L2 | action_recognition | boundary 2.5 | 5 | 4 | 5 |  | - | - |
| L2 | event_object_role | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | sound_anchored_spatial_near | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L2 | sound_anchored_spatial_side | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L2 | sound_movement_binding | boundary<1 | 5 | 2 | 5 |  | - | - |
| L3 | cross_event_integration | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L3 | hidden_state_inference | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | spatial_state_integration | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | causal_prerequisite_reasoning | boundary 1.75 | 6 | 4 | 6 |  | - | - |
| L4 | goal_conditioned_planning | boundary 3.5 | 3 | 3 | 3 |  | - | - |

## L1 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 5 seconds into the clip, when the camera wearer pushes out some breadcrumbs, what object are they holdin |
| 2 | DIAG | object_recognition | single_choice | same_skill_new_event | - | correct | B | B | At the start of the clip, while placing the breadcrumbs container away, the camera wearer picks up a grey bowl |
| 3 | DIAG | object_recognition | single_choice | coverage | - | correct | B | B | About 6 seconds into the clip, when the camera wearer pours out some flour using their right hand, what object |
| 4 | DIAG | object_recognition | single_choice | same_skill_new_event | - | correct | B | B | About 5 seconds into the clip, when the camera wearer transfers an item from their left hand to their right ha |
| 5 | DIAG | object_recognition | short_answer | coverage | - | correct | a ball of dough | potato chicken ball | About 7 seconds into the clip, when the camera wearer retrieves more flour using their right hand, what object |
| 6 | DIAG | object_recognition | short_answer | same_skill_new_event | - | wrong | a dough ball | a chicken ball | About 5 seconds into the clip, when the camera wearer retrieves an item from the bowl of eggs using their righ |
| 7 | DIAG | object_recognition | single_choice | same_skill_new_event | - | correct | C | C | About 5 seconds into the clip, when the camera wearer moves the breadcrumb cup across the counter surface usin |
| 8 | DIAG | object_recognition | single_choice | coverage | - | correct | B | B | About 5 seconds into the clip, when the camera wearer scoops up tiny bits of mixture from the foil using their |
| 9 | DIAG | object_location_at_time | single_choice | coverage | - | wrong | C | A | About 6 seconds into the clip, when the camera wearer coats the chicken ball, where do they place it? |
| 10 | DIAG | object_location_at_time | single_choice | same_skill_new_event | - | correct | A | A | At the end of the clip, when the camera wearer stores the container of breadcrumbs, where do they place it? |
| 11 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 5 seconds into the clip, when the camera wearer retrieves the chicken ball from the bowl of egg, where d |
| 12 | DIAG | object_location_at_time | single_choice | same_skill_new_event | - | correct | A | A | About 5 seconds into the clip, when the camera wearer rolls the second chicken ball in the flour bowl, where d |
| 13 | DIAG | object_location_at_time | single_choice | same_skill_new_event | - | wrong | B | A | About 5 seconds into the clip, when the camera wearer retrieves the chicken ball using their right hand, where |
| 14 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.05336, 0.73673, 0.05865, 0. | 51.3, 72.5, 57.8, 80.0 | Please provide the bounding box for the lid of breadcrumb container in the first frame of the clip. |
| 15 | DIAG | object_grounding | bbox | same_skill_new_event | - | correct | [0.417, 0.646, 0.503, 0.747] | 44.1, 64.4, 53.0, 74.4 | Please provide the bounding box for the grey bowl of flour in the first frame of the clip. |
| 16 | DIAG | object_grounding | bbox | same_skill_new_event | - | wrong | [0.357, 0.745, 0.577, 0.949] | 47.0, 74.7, 58.8, 94.0 | Please provide the bounding box for the tupperware of flour in the first frame of the clip. |
| 17 | DIAG | object_grounding | bbox | same_skill_new_event | - | wrong | [0.722, 0.0, 0.998, 0.391] | 25.3, 90.1, 42.7, 98.6 | Please provide the bounding box for the tea towel in the first frame of the clip. |

## L2 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | sound_action_binding | - | request_verification | - | evidence_unresolved | None | None |  |
| 2 | DIAG | sound_action_binding | single_choice | coverage | - | wrong | B | A | During the clip, a distinct sound of a plastic object hitting metal is heard. Which of the following actions p |
| 3 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | During the clip, a squishing or kneading sound is heard. Which action produces this sound? |
| 4 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | correct | C | C | During the clip, a brief clinking or tapping sound is heard. Which action produces this sound? |
| 5 | DIAG | sound_action_binding | single_choice | coverage | - | correct | C | C | During the clip, a distinct sound of a metal object hitting a wooden surface is heard. Which action produces t |
| 6 | DIAG | sound_action_binding | single_choice | coverage | - | wrong | B | A | During the clip, a ceramic clinking sound is heard. Which of the following actions produces this sound? |
| 7 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the camera wearer picks up the container of breadcrumbs, where is it placed? |
| 8 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | After the camera wearer coats the chicken ball with flour, into which container is the ball moved next? |
| 9 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | After the camera wearer dips the chicken ball in the egg, into which container is it moved next? |
| 10 | DIAG | object_state_change | - | - | - | env_failure | None | None |  |
| 11 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the camera wearer picks up the uncoated potato chicken ball to roll it in the flour, from where is it pic |
| 12 | DIAG | object_state_change | short_answer | coverage | - | correct | the bowl of breadcrumbs | the breadcrumbs bowl | After the camera wearer dips the chicken ball in the egg, into which container is it moved next? |
| 13 | DIAG | object_state_change | short_answer | same_event_new_format | - | correct | On the top shelf of the cabine | in the cabinet | When the camera wearer picks up the container of breadcrumbs, where is it placed? |
| 14 | DIAG | action_temporal_order | single_choice | coverage | - | correct | B | B | Which of the following actions happens immediately before the camera wearer pours the breadcrumbs into a bowl? |
| 15 | DIAG | action_temporal_order | single_choice | coverage | - | wrong | B | A | Which of the following actions happens immediately after the camera wearer places the lid back on the breadcru |
| 16 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | Which of the following actions happens immediately before the camera wearer pours the flour into the bowl? |
| 17 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | Which of the following actions happens immediately after the camera wearer empties the tupperware of flour int |
| 18 | DIAG | action_temporal_order | single_choice | coverage | - | correct | B | B | Which of the following actions happens immediately before the camera wearer sprinkles breadcrumbs on top of th |
| 19 | DIAG | action_temporal_order | single_choice | coverage | - | wrong | B | A | Which of the following actions happens immediately before the camera wearer picks up the uncoated potato chick |
| 20 | DIAG | action_recognition | single_choice | coverage | - | correct | C | C | After walking to the cooking station, what does the camera wearer do with the breadcrumbs they are holding? |
| 21 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | While adjusting the scale, what action does the camera wearer perform with the grey bowl of flour? |
| 22 | DIAG | action_recognition | single_choice | coverage | - | wrong | D | A | After bringing the bag of flour out of the cabinet, what action does the camera wearer perform to transfer the |
| 23 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | How does the camera wearer apply flour to the chicken and potato ball? |
| 24 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | What action does the camera wearer perform to ensure the chicken ball is evenly coated with egg? |
| 25 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | When the camera wearer pours the breadcrumbs into a bowl, what object are they poured from? |
| 26 | DIAG | event_object_role | single_choice | coverage | - | correct | B | B | After opening the cabinet, what object does the camera wearer place inside it? |
| 27 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | When the camera wearer pours the flour, into what object is it poured? |
| 28 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | When the camera wearer empties the tupperware container, into what object is it emptied? |
| 29 | DIAG | event_object_role | short_answer | coverage | - | correct | A bowl of eggs | a bowl of egg | When the camera wearer dips the chicken ball, into what object is it dipped? |
| 30 | DIAG | event_object_role | short_answer | coverage | - | correct | the foil | the foil | When the camera wearer picks up the uncoated potato chicken ball, from what object is it picked up? |
| 31 | DIAG | sound_movement_binding | single_choice | coverage | - | wrong | C | A | When the camera wearer places the breadcrumbs container away in a storage area, which movement produces the di |
| 32 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | When the camera wearer rolls the chicken ball in the flour bowl to coat it, which movement produces the distin |
| 33 | DIAG | sound_movement_binding | single_choice | coverage | - | wrong | B | A | When the camera wearer dips the floured chicken ball into the egg bowl, which movement produces the brief clin |
| 34 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | When the camera wearer rolls the second chicken ball in the flour bowl, which movement produces the distinct s |
| 35 | DIAG | sound_movement_binding | single_choice | coverage | - | wrong | D | C | When the camera wearer dips the second chicken ball into the egg bowl, which movement produces the ceramic cli |

## L3 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | cross_event_integration | single_choice | coverage | - | correct | C | C | Before the container was stored away in the cabinet, what was dispensed from it? |
| 2 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | What was the chicken ball coated with just before it was dipped in the egg? |
| 3 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | Before shaping the second chicken mixture into a ball, what was the final step done to the first chicken ball? |
| 4 | DIAG | cross_event_integration | single_choice | coverage | - | correct | B | B | What was the coating on the second chicken ball just before it was dipped in the egg? |
| 5 | DIAG | cross_event_integration | short_answer | coverage | - | correct | Breadcrumbs | breadcrumbs | Before placing the bowl for flour on the scale surface, what ingredient was put into the other bowl? |
| 6 | DIAG | cross_event_integration | short_answer | same_skill_new_event | - | correct | Breadcrumbs | Breadcrumbs | Before placing the bowl for flour on the scale surface, what was poured into the first bowl? |
| 7 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | A | A | What was done with the grey bowl before the flour was poured into it? |
| 8 | DIAG | causal_prerequisite_reasoning | single_choice | same_skill_new_event | - | correct | A | A | What was done to prepare the grey bowl before the chicken ball was coated using its contents? |
| 9 | DIAG | causal_prerequisite_reasoning | single_choice | same_skill_new_event | - | correct | A | A | Before the flour was poured into the grey bowl, what was done to prepare the bowl? |
| 10 | DIAG | causal_prerequisite_reasoning | single_choice | same_skill_new_event | - | wrong | B | A | What was done to prepare the bowl before the chicken ball was rolled in it? |
| 11 | DIAG | causal_prerequisite_reasoning | single_choice | same_skill_new_event | - | correct | A | A | Which action was performed to provide a container for the flour before it was poured? |
| 12 | DIAG | causal_prerequisite_reasoning | single_choice | same_skill_new_event | - | wrong | B | A | What ingredient was added to the bowl before the chicken ball was rolled in it? |

## L4 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | B | B | What is the next step the person should take to continue the task the camera wearer is doing? |
| 2 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | B | B | What is the next step the person should take to continue the task the camera wearer is doing? |
| 3 | DIAG | goal_conditioned_planning | plan | coverage | - | correct | ['Coat the remaining chicken b | 1. Shape the second chicken ba | What are the remaining stages, in order, for the task the camera wearer is doing? |

## Gemini 用量

| role | calls | errors | tok_in | tok_out | tok_think |
|---|---|---|---|---|---|
| examiner | 89 | 1 | 2262651 | 53884 | 318028 |
| judge | 7 | 0 | 3095 | 706 | 3429 |
| scope | 1 | 0 | 1690 | 3026 | 3858 |
| solver | 195 | 0 | 864030 | 3227 | 0 |
