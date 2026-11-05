# pyramid2 run `p2_hdepicE_1023t_g4_v16_goldlive__55`

dataset hdepic_e · videos 1 · examiner `gcp/google/gemini-3.1-pro-preview` · solver `gcp/google/gemini-4-argon` · n_per_layer 200 · seed 1023 · prompt physical-mental-draft2-hdepic-e+v16sg

**结果为 provisional**:gold = Examiner 的 proposed_reference_answer,未经人工核验;open/plan 题由 Gemini judge 判。

## 每层概览

| layer | stop | turns | scored | correct | raw acc | cluster-dedup acc | follow-up | invalid/unresolved | confirmation |
|---|---|---|---|---|---|---|---|---|---|
| L1 | STAIRCASE_COMPLETE | 18 | 18 | 12 | 0.667 | 0.643 | 0 | 0/0 | - |
| L2 | STAIRCASE_COMPLETE | 40 | 38 | 31 | 0.816 | 0.824 | 0 | 0/2 | - |
| L3 | STAIRCASE_COMPLETE | 12 | 12 | 11 | 0.917 | 0.917 | 0 | 0/0 | - |
| L4 | STAIRCASE_COMPLETE | 5 | 5 | 3 | 0.6 | 0.6 | 0 | 0/0 | - |

## 每层 × skill 诊断结论

| layer | skill | verdict | scored | correct | clusters | first-try correct | supported hypotheses | confirmation |
|---|---|---|---|---|---|---|---|---|
| L1 | spatial_near | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L1 | spatial_side | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L1 | object_recognition | boundary 3 | 9 | 7 | 6 |  | - | - |
| L1 | object_location_at_time | boundary 2.25 | 6 | 5 | 5 |  | - | - |
| L1 | object_grounding | boundary<1 | 3 | 0 | 3 |  | - | - |
| L2 | sound_action_binding | boundary<1 | 6 | 3 | 5 |  | - | - |
| L2 | object_state_change | boundary>=4 | 6 | 6 | 5 |  | - | - |
| L2 | action_temporal_order | boundary 3.5 | 8 | 7 | 6 |  | - | - |
| L2 | action_recognition | boundary 3.5 | 7 | 6 | 7 |  | - | - |
| L2 | event_object_role | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | sound_anchored_spatial_near | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L2 | sound_anchored_spatial_side | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L2 | sound_movement_binding | boundary 1.5 | 5 | 3 | 5 |  | - | - |
| L3 | cross_event_integration | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L3 | hidden_state_inference | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | spatial_state_integration | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | causal_prerequisite_reasoning | boundary 2 | 6 | 5 | 6 |  | - | - |
| L4 | goal_conditioned_planning | boundary 1.25 | 5 | 3 | 5 |  | - | - |

## L1 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 8 seconds into the clip, the camera wearer pours breadcrumbs. What object are the breadcrumbs poured int |
| 2 | DIAG | object_recognition | single_choice | same_skill_new_event | - | correct | A | A | About 4 seconds into the clip, the camera wearer replaces a lid. What object is the lid placed onto? |
| 3 | DIAG | object_recognition | single_choice | same_skill_new_event | - | correct | A | A | About 6 seconds into the clip, the camera wearer places their right hand back into an object to retrieve more  |
| 4 | DIAG | object_recognition | single_choice | same_skill_new_event | - | correct | A | A | About 6 seconds into the clip, during the event to roll the chicken ball in the flour bowl to coat it, the cam |
| 5 | DIAG | object_recognition | short_answer | coverage | - | wrong | a bowl | tupperware | About 4 seconds into the clip, during the event to shape the second chicken and cheese mixture into a ball, th |
| 6 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 6 seconds into the clip, during the event to roll the second chicken ball in a bowl, what object is the  |
| 7 | DIAG | object_recognition | single_choice | coverage | - | wrong | D | B | About 7 seconds into the clip, during the event to place the breadcrumbs container away in a storage area, the |
| 8 | DIAG | object_recognition | single_choice | coverage | - | correct | C | C | At the start of the clip, during the event to roll the chicken ball in the flour bowl to coat it, the camera w |
| 9 | DIAG | object_recognition | single_choice | same_event_new_format | - | correct | A | A | About 2 seconds into the clip, during the event to shape the second chicken and cheese mixture into a ball, th |
| 10 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 8 seconds into the clip, during the event to roll the chicken ball in the flour bowl to coat it, the cam |
| 11 | DIAG | object_location_at_time | single_choice | same_skill_new_event | - | correct | A | A | About 7 seconds into the clip, during the event to store the breadcrumbs container, the camera wearer moves th |
| 12 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 6 seconds into the clip, during the event to dip the floured chicken ball into the egg bowl, the camera  |
| 13 | DIAG | object_location_at_time | single_choice | same_skill_new_event | - | correct | A | A | About 5 seconds into the clip, during the event to roll the second chicken ball in the flour bowl, the camera  |
| 14 | DIAG | object_location_at_time | short_answer | coverage | - | wrong | the bowl of bread crumbs | counter | About 5 seconds into the clip, during the event to dip the floured chicken ball into the egg bowl, the camera  |
| 15 | DIAG | object_location_at_time | single_choice | same_skill_new_event | - | correct | C | C | About 7 seconds into the clip, during the event to prepare the bowl for the flour, the camera wearer moves the |
| 16 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.39, 0.68, 0.43, 0.76] | 51.3, 72.5, 57.8, 80.0 | At the start of the clip, during the event to pour breadcrumbs from the container into a bowl, what is the bou |
| 17 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.4, 0.64, 0.51, 0.74] | 44.1, 64.4, 53.0, 74.4 | At the start of the clip, during the event to pour breadcrumbs from the container into a bowl, what is the bou |
| 18 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.396, 0.708, 0.608, 0.938] | 47.0, 74.7, 58.8, 94.0 | At the start of the clip, during the event to roll the chicken ball in the flour bowl to coat it, what is the  |

## L2 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | sound_action_binding | - | request_verification | - | evidence_unresolved | None | None |  |
| 2 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | During the process of placing the breadcrumbs container away in the cabinet, a distinct collision sound is hea |
| 3 | DIAG | sound_action_binding | single_choice | coverage | - | wrong | D | A | When the camera wearer rolls and shapes the chicken and potato mixture into a ball with both hands, which of t |
| 4 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | During the clip, a distinct collision sound is heard. Which action produces this sound? |
| 5 | DIAG | sound_action_binding | single_choice | coverage | - | wrong | B | A | During the clip, the camera wearer returns the bowl of flour to the counter surface. Which of the following so |
| 6 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | When the camera wearer dips the chicken ball into the bowl of egg, which of the following sounds is produced? |
| 7 | DIAG | sound_action_binding | single_choice | coverage | - | wrong | B | C | During the clip, a collision sound involving metal and plastic is heard. Which action produces this sound? |
| 8 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the camera wearer puts the container of breadcrumbs away, where is it placed? |
| 9 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the camera wearer dips and turns the potato chicken ball in the bowl to coat it, where does the ball move |
| 10 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the camera wearer retrieves the chicken ball from the egg bowl, where is it placed next? |
| 11 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the camera wearer picks up the uncoated potato chicken ball from the foil, where does the ball move in te |
| 12 | DIAG | object_state_change | short_answer | coverage | - | correct | in the bowl of breadcrumbs | in the bowl of breadcrumbs | After the camera wearer retrieves the potato chicken ball from the bowl of eggs and sprinkles flour over it, w |
| 13 | DIAG | object_state_change | short_answer | same_event_new_format | - | correct | The top shelf of the cabinet | in the cabinet | When the camera wearer puts the container of breadcrumbs away, where is it placed? |
| 14 | DIAG | action_temporal_order | - | request_verification | - | evidence_unresolved | None | None |  |
| 15 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the clip, the camera wearer places a bowl on the counter and stores the breadcrumbs container in a cabi |
| 16 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the clip, the camera wearer interacts with flour and a bowl. Which of the following describes the order |
| 17 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the clip, the camera wearer shapes the first chicken ball and dips it in egg. Which of the following de |
| 18 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the clip, the camera wearer interacts with the chicken ball, egg, and breadcrumbs. Which of the followi |
| 19 | DIAG | action_temporal_order | short_answer | coverage | - | correct | Sprinkle flour onto the second | coat the chicken ball with flo | During the clip, the camera wearer rolls the second chicken ball in both hands so that it is in a better shape |
| 20 | DIAG | action_temporal_order | short_answer | coverage | - | wrong | moulds the potato chicken ball | place the potato chicken ball  | During the clip, the camera wearer sprinkles flour over the potato chicken ball. What action involving the pot |
| 21 | DIAG | action_temporal_order | single_choice | coverage | - | correct | B | B | During the clip, the camera wearer places a bowl on the counter and stores the breadcrumbs container in a cabi |
| 22 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the clip, the camera wearer interacts with flour and a bowl. Which of the following describes the order |
| 23 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the clip, the camera wearer interacts with the lid of breadcrumbs and a bowl. What action does the came |
| 24 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the clip, the camera wearer interacts with the cup of breadcrumbs. What action does the camera wearer p |
| 25 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the clip, the camera wearer interacts with a bag of flour and a bowl. What action does the camera weare |
| 26 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the clip, the camera wearer interacts with the chicken ball and flour. What action does the camera wear |
| 27 | DIAG | action_recognition | short_answer | coverage | - | wrong | Moves the chicken ball from th | dips the chicken ball into the | During the clip, the camera wearer interacts with the chicken ball and the bowl of egg. What action does the c |
| 28 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the clip, the camera wearer interacts with the chicken mixture. What action does the camera wearer perf |
| 29 | DIAG | action_recognition | single_choice | coverage | - | correct | C | C | During the clip, the camera wearer interacts with the chicken ball and the bowl of breadcrumbs. What action do |
| 30 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | During the clip, the camera wearer pours breadcrumbs. What container are the breadcrumbs poured into? |
| 31 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | During the clip, the camera wearer places an object onto the scale. Which object is placed there? |
| 32 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | During the clip, the camera wearer pours flour. What container is the flour poured into? |
| 33 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | During the clip, the camera wearer empties a plastic container of flour. What is the flour emptied into? |
| 34 | DIAG | event_object_role | short_answer | coverage | - | correct | a bowl | a bowl of egg | During the clip, the camera wearer dips the potato chicken ball. What container is it dipped into? |
| 35 | DIAG | event_object_role | short_answer | coverage | - | correct | the foil | foil | During the clip, the camera wearer picks up the uncoated potato chicken ball and scoops up tiny bits of mixtur |
| 36 | DIAG | sound_movement_binding | single_choice | coverage | - | wrong | B | A | During the clip, a sound of metal and plastic colliding is heard. Which object's movement produces this sound? |
| 37 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | When the camera wearer coats the chicken ball with flour, a collision sound involving plastic and ceramic is h |
| 38 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | During the clip, a kneading sound is heard. Which object's movement produces this sound? |
| 39 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | When the camera wearer rolls the second chicken ball in the flour bowl, a collision sound involving metal and  |
| 40 | DIAG | sound_movement_binding | single_choice | coverage | - | wrong | B | A | During the clip, the camera wearer dips a food item into the bowl of egg, and a ceramic collision sound is hea |

## L3 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | What ingredient was dispensed from the container before it was stored away in the cabinet? |
| 2 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | What was the coating on the chicken ball just before it was dipped in the egg? |
| 3 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | Before the person shapes the second chicken ball, what was the final coating applied to the first chicken ball |
| 4 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | What was the coating on the second chicken ball just before it was dipped in the egg? |
| 5 | DIAG | cross_event_integration | short_answer | coverage | - | correct | Breadcrumbs | breadcrumbs | Before the person places the bowl for the flour on the scale, what ingredient had they poured into a bowl? |
| 6 | DIAG | cross_event_integration | short_answer | coverage | - | correct | the container of breadcrumbs | The breadcrumbs container | Before the person retrieves the flour from the cabinet, what item had they just stored in that same cabinet? |
| 7 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | A | A | Before the person pours the flour into the bowl, what necessary preparation step did they take regarding that  |
| 8 | DIAG | causal_prerequisite_reasoning | single_choice | same_skill_new_event | - | correct | A | A | Before the person rotates and rolls the first chicken ball to coat it, what ingredient had they poured into th |
| 9 | DIAG | causal_prerequisite_reasoning | single_choice | same_skill_new_event | - | correct | A | A | Before the person pours the flour, what necessary preparation step did they take regarding the bowl that recei |
| 10 | DIAG | causal_prerequisite_reasoning | single_choice | same_skill_new_event | - | wrong | B | A | Before the person rolls the chicken ball to coat it, what ingredient had they poured into the bowl? |
| 11 | DIAG | causal_prerequisite_reasoning | single_choice | same_skill_new_event | - | correct | B | B | Before pouring the flour, what did the person do to prepare the bowl that receives it? |
| 12 | DIAG | causal_prerequisite_reasoning | single_choice | same_skill_new_event | - | correct | A | A | Before the person rolls the chicken ball to coat it, what ingredient had they poured into the bowl? |

## L4 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | goal_conditioned_planning | single_choice | coverage | - | wrong | C | B | Based on the progress shown in the clip, what is the next step the person should take to continue the task the |
| 2 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | B | B | Based on the progress shown in the clip, what is the next step the person should take to continue the task the |
| 3 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | B | B | Based on the progress shown in the clip, what is the next step the person should take to continue the task the |
| 4 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | A | A | Based on the progress shown in the clip, what is the next step the person should take to continue the task the |
| 5 | DIAG | goal_conditioned_planning | single_choice | coverage | - | wrong | A | B | Based on the progress shown in the clip, what is the next step the person should take to continue the task the |

## Gemini 用量

| role | calls | errors | tok_in | tok_out | tok_think |
|---|---|---|---|---|---|
| examiner | 84 | 0 | 2241183 | 51069 | 285895 |
| judge | 16 | 0 | 4729 | 852 | 1889 |
| solver | 219 | 0 | 990651 | 3567 | 0 |
