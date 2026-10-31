# pyramid2 run `p2_hdepicE_1023t_g4_v17_goldlive__55`

dataset hdepic_e · videos 1 · examiner `gcp/google/gemini-3.1-pro-preview` · solver `gcp/google/gemini-4-argon` · n_per_layer 200 · seed 1023 · prompt physical-mental-draft2-hdepic-e+v16sg

**结果为 provisional**:gold = Examiner 的 proposed_reference_answer,未经人工核验;open/plan 题由 Gemini judge 判。

## 每层概览

| layer | stop | turns | scored | correct | raw acc | cluster-dedup acc | follow-up | invalid/unresolved | confirmation |
|---|---|---|---|---|---|---|---|---|---|
| L1 | EVENT_LOOP_COMPLETE | 25 | 25 | 12 | 0.48 | 0.48 | 0 | 0/0 | - |
| L2 | EVENT_LOOP_COMPLETE | 58 | 58 | 44 | 0.759 | 0.759 | 0 | 0/0 | - |
| L3 | EVENT_LOOP_COMPLETE | 14 | 14 | 12 | 0.857 | 0.857 | 0 | 0/0 | - |
| L4 | STAIRCASE_COMPLETE | 5 | 5 | 4 | 0.8 | 0.8 | 0 | 0/0 | - |

## 每层 × skill 诊断结论

| layer | skill | verdict | scored | correct | clusters | first-try correct | supported hypotheses | confirmation |
|---|---|---|---|---|---|---|---|---|
| L1 | spatial_near | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L1 | spatial_side | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L1 | object_recognition | boundary 3.5 | 12 | 9 | 12 |  | - | - |
| L1 | object_location_at_time | boundary 1.75 | 5 | 3 | 5 |  | - | - |
| L1 | object_grounding | boundary<1 | 8 | 0 | 8 |  | - | - |
| L2 | sound_action_binding | boundary 2.5 | 9 | 7 | 9 |  | - | - |
| L2 | object_state_change | boundary 3.5 | 5 | 5 | 5 |  | - | - |
| L2 | action_temporal_order | boundary 3 | 12 | 7 | 12 |  | - | - |
| L2 | action_recognition | boundary 2.5 | 12 | 11 | 12 |  | - | - |
| L2 | event_object_role | boundary 3 | 12 | 9 | 12 |  | - | - |
| L2 | sound_anchored_spatial_near | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L2 | sound_anchored_spatial_side | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L2 | sound_movement_binding | boundary 1.5 | 8 | 5 | 8 |  | - | - |
| L3 | cross_event_integration | boundary>=4 | 12 | 10 | 12 |  | - | - |
| L3 | hidden_state_inference | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | spatial_state_integration | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | causal_prerequisite_reasoning | boundary 2.0 | 2 | 2 | 2 |  | - | - |
| L4 | goal_conditioned_planning | boundary 1.75 | 5 | 4 | 5 |  | - | - |

## L1 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 8 seconds into the clip, when the camera wearer pours the breadcrumbs, what object are they pouring them |
| 2 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.517, 0.708, 0.583, 0.767] | 51.3, 72.5, 57.8, 80.0 | In the first frame of the clip, what is the bounding box of the lid of breadcrumb container? |
| 3 | DIAG | object_recognition | single_choice | same_skill_new_event | - | correct | B | B | At the start of the clip, when the camera wearer picks up a bowl with their left hand, what object are they ho |
| 4 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | At the end of the clip, when the camera wearer places the container of breadcrumbs away, where do they place i |
| 5 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.57, 0.83, 0.66, 0.93] | 41.9, 78.1, 48.9, 86.5 | In the first frame of the clip, what is the bounding box of the lid of breadcrumb container? |
| 6 | DIAG | object_recognition | single_choice | coverage | - | correct | C | C | About 6 seconds into the clip, when the camera wearer pours out some flour using their right hand, what object |
| 7 | DIAG | object_recognition | single_choice | coverage | - | correct | C | C | About 5 seconds into the clip, when the camera wearer pours out the flour using their right hand, what object  |
| 8 | DIAG | object_recognition | short_answer | coverage | - | correct | flour | flour | At the start of the clip, when the camera wearer shapes the chicken and cheese mixture into a ball using their |
| 9 | DIAG | object_recognition | short_answer | coverage | - | wrong | a chicken ball | tupperware of flour | About 4 seconds into the clip, when the camera wearer rolls the chicken ball in the flour bowl to coat it, wha |
| 10 | DIAG | object_location_at_time | single_choice | coverage | - | wrong | B | A | About 8 seconds into the clip, when the camera wearer rolls the chicken ball in the flour bowl to coat it, whe |
| 11 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.503, 0.628, 0.597, 0.722] | 47.0, 74.7, 58.8, 94.0 | In the first frame of the clip, what is the bounding box of the tupperware of flour? |
| 12 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 5 seconds into the clip, when the camera wearer retrieves the chicken ball, what object are they retriev |
| 13 | DIAG | object_location_at_time | single_choice | coverage | - | wrong | C | A | About 6 seconds into the clip, when the camera wearer dips the floured chicken ball, where do they place it? |
| 14 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.542, 0.708, 0.608, 0.774] | 53.3, 69.4, 57.6, 75.2 | In the first frame of the clip, what is the bounding box of the potato chicken ball? |
| 15 | DIAG | object_recognition | single_choice | coverage | - | correct | C | C | About 6 seconds into the clip, when the camera wearer scoops up tiny bits of potato chicken mixture using thei |
| 16 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 5 seconds into the clip, when the camera wearer picks up the uncoated potato chicken ball to roll it in  |
| 17 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.52, 0.85, 0.62, 1.0] | 25.3, 90.1, 42.7, 98.6 | In the first frame of the clip, what is the bounding box of the tea towel? |
| 18 | DIAG | object_recognition | short_answer | coverage | - | wrong | dough | potato chicken ball | About 7 seconds into the clip, when the camera wearer retrieves more flour using their right hand, what object |
| 19 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.496, 0.845, 0.558, 0.916] | 50.6, 73.0, 55.7, 77.8 | In the first frame of the clip, what is the bounding box of the potato chicken ball? |
| 20 | DIAG | object_recognition | short_answer | coverage | - | correct | the bowl | bowl of eggs | About 5 seconds into the clip, when the camera wearer retrieves the potato chicken ball using their right hand |
| 21 | DIAG | object_location_at_time | single_choice | coverage | - | correct | C | C | About 5 seconds into the clip, when the camera wearer retrieves the dipped potato chicken ball, where do they  |
| 22 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.604, 0.788, 0.639, 0.822] | 48.9, 73.5, 54.7, 80.5 | In the first frame of the clip, what is the bounding box of the potato chicken ball? |
| 23 | DIAG | object_recognition | short_answer | coverage | - | wrong | A dough ball in their left han | potato chicken ball | About 5 seconds into the clip, when the camera wearer sprinkles flour using their right hand, what object are  |
| 24 | DIAG | object_recognition | short_answer | coverage | - | correct | a dough ball | a potato chicken ball | About 7 seconds into the clip, when the camera wearer picks up breadcrumbs using their right hand, what object |
| 25 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.472, 0.767, 0.528, 0.823] | 47.7, 74.5, 51.1, 80.5 | In the first frame of the clip, what is the bounding box of the potato chicken ball? |

## L2 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | sound_action_binding | single_choice | coverage | - | wrong | B | A | During the task the camera wearer is doing, which action produces the clattering sounds heard shortly before t |
| 2 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, which of these actions happens after the cup of breadcrumbs is pla |
| 3 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, what does the wearer do with the lid of breadcrumbs after walking  |
| 4 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, what does the wearer pour the breadcrumbs into? |
| 5 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, which action produces the sharp sound heard immediately after the  |
| 6 | DIAG | object_state_change | single_choice | coverage | - | correct | C | C | During the task the camera wearer is doing, where does the wearer place the container of breadcrumbs to store  |
| 7 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, which of these actions happens immediately before the wearer picks |
| 8 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, what does the wearer do with the breadcrumbs container after openi |
| 9 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, which object does the wearer place into the cabinet? |
| 10 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, which movement produces the impact sound heard immediately after t |
| 11 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, which of these actions happens immediately after the wearer brings |
| 12 | DIAG | action_recognition | single_choice | same_skill_new_event | - | wrong | C | A | During the task the camera wearer is doing, how does the wearer extract the flour from the bag? |
| 13 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | C | C | During the task the camera wearer is doing, which object does the wearer retrieve from the cabinet? |
| 14 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | B | B | During the task the camera wearer is doing, which of these actions happens immediately after the wearer pours  |
| 15 | DIAG | action_recognition | single_choice | coverage | - | correct | C | C | During the task the camera wearer is doing, how does the wearer transfer the flour into the bowl? |
| 16 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | B | B | During the task the camera wearer is doing, what does the wearer pour the flour into? |
| 17 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, which action produces the kneading sound heard in the clip? |
| 18 | DIAG | action_temporal_order | short_answer | same_skill_new_event | - | wrong | dips the ball into the beaten  | picks up the container of flou | During the task the camera wearer is doing, what does the wearer do immediately after rolling the flour-coated |
| 19 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, how does the wearer coat the chicken and potato ball with flour? |
| 20 | DIAG | event_object_role | short_answer | same_skill_new_event | - | correct | the chicken and cheese mixture | chicken and cheese mixture | During the task the camera wearer is doing, what does the wearer shape into a ball using their hands? |
| 21 | DIAG | sound_movement_binding | single_choice | coverage | - | wrong | D | A | During the task the camera wearer is doing, which movement produces the plastic and ceramic collision sound he |
| 22 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | correct | B | B | During the task the camera wearer is doing, which action produces the sharp clattering sound heard immediately |
| 23 | DIAG | object_state_change | single_choice | same_skill_new_event | - | correct | B | B | During the task the camera wearer is doing, where does the wearer place the potato chicken ball immediately af |
| 24 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | wrong | B | A | During the task the camera wearer is doing, which of these actions happens immediately after the wearer rolls  |
| 25 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, how does the wearer coat the potato chicken ball with egg? |
| 26 | DIAG | event_object_role | short_answer | same_skill_new_event | - | wrong | the sink | the bowl of flour | During the task the camera wearer is doing, what does the wearer empty the tupperware of flour into? |
| 27 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, which movement produces the plastic and ceramic collision sound he |
| 28 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, which action produces the continuous rustling and rubbing sound he |
| 29 | DIAG | object_state_change | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, into which container does the wearer transfer the potato chicken b |
| 30 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, which of these actions happens immediately after the wearer retrie |
| 31 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, how does the wearer coat the egg-washed potato chicken ball with b |
| 32 | DIAG | event_object_role | single_choice | same_skill_new_event | - | wrong | B | A | During the task the camera wearer is doing, what does the wearer dip the potato chicken ball into? |
| 33 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, which movement produces the sharp collision sound heard while the  |
| 34 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, which action produces the metal and wood collision sound heard whi |
| 35 | DIAG | object_state_change | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, where does the wearer retrieve the uncoated potato chicken ball fr |
| 36 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, which of these actions happens immediately after the wearer return |
| 37 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, what does the wearer do with the bowl of flour while picking up th |
| 38 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, which object does the wearer pick up from the foil while returning |
| 39 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, which movement produces the metal and wood collision sound heard w |
| 40 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, which action produces the plastic and wood collision sound heard w |
| 41 | DIAG | action_temporal_order | single_choice | coverage | - | wrong | B | A | During the task the camera wearer is doing, which of these actions happens immediately before the wearer trans |
| 42 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, how does the wearer shape the second potato chicken ball? |
| 43 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, which object does the wearer roll in both hands to give it a bette |
| 44 | DIAG | sound_movement_binding | single_choice | coverage | - | wrong | C | A | During the task the camera wearer is doing, which movement produces the plastic and wood collision sound heard |
| 45 | DIAG | sound_action_binding | short_answer | coverage | - | wrong | two bowls colliding | moving the chicken ball in the | During the task the camera wearer is doing, which action produces the ceramic collision sound heard while the  |
| 46 | DIAG | object_state_change | short_answer | same_skill_new_event | - | correct | bowl of breadcrumbs | the bowl of breadcrumbs | During the task the camera wearer is doing, into which container does the wearer place the second potato chick |
| 47 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | wrong | A | B | During the task the camera wearer is doing, which of these actions happens immediately before the wearer dips  |
| 48 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, how does the wearer coat the potato chicken ball with egg? |
| 49 | DIAG | event_object_role | single_choice | same_skill_new_event | - | wrong | B | A | During the task the camera wearer is doing, what does the wearer dip the potato chicken ball into? |
| 50 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | wrong | D | A | During the task the camera wearer is doing, which movement produces the ceramic collision sound heard while th |
| 51 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, which action produces the metal and wood collision sound heard whi |
| 52 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, which of these actions happens immediately after the wearer sprink |
| 53 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, how does the wearer apply extra flour to the potato chicken ball? |
| 54 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, what does the wearer sprinkle extra flour onto? |
| 55 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, which movement produces the metal and wood collision sound heard w |
| 56 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | wrong | D | A | During the task the camera wearer is doing, which of these actions happens immediately before the wearer place |
| 57 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, how does the wearer coat the second potato chicken ball with bread |
| 58 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, when the wearer coats the second potato chicken ball with breadcru |

## L3 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | When the camera wearer places the grey bowl on the scale, which of the following is true about this bowl? |
| 2 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | Before the container is stored away in the cabinet, what was poured out of it? |
| 3 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | B | B | Before the camera wearer retrieves the bag of flour from the cabinet, what object did they put into that same  |
| 4 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | A | A | Which earlier action was a necessary physical prerequisite for pouring the flour into the grey bowl? |
| 5 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | When the camera wearer rolls the chicken ball to coat it with flour, how was the flour initially placed into t |
| 6 | DIAG | causal_prerequisite_reasoning | single_choice | same_skill_new_event | - | correct | B | B | Which earlier action was a necessary physical prerequisite for rolling the chicken ball to coat it with flour? |
| 7 | DIAG | cross_event_integration | short_answer | coverage | - | correct | flour and raw egg | flour and egg | Before the camera wearer rolls the chicken ball in the breadcrumbs bowl, what two ingredients was it coated wi |
| 8 | DIAG | cross_event_integration | short_answer | same_skill_new_event | - | correct | flour | flour | What was the coating on the chicken ball just before it was dipped in the egg? |
| 9 | DIAG | cross_event_integration | short_answer | same_skill_new_event | - | correct | Breadcrumbs | breadcrumbs | Before the camera wearer picks up the second uncoated chicken ball, what was the final ingredient applied to t |
| 10 | DIAG | cross_event_integration | short_answer | same_skill_new_event | - | correct | Egg mixture and breadcrumbs | egg and breadcrumbs | When the camera wearer picks up the second uncoated chicken ball, what were the last two ingredients applied t |
| 11 | DIAG | cross_event_integration | short_answer | same_skill_new_event | - | wrong | flour | breadcrumbs | Before the camera wearer shapes the second chicken mixture into a ball, what was the final ingredient they coa |
| 12 | DIAG | cross_event_integration | short_answer | same_skill_new_event | - | wrong | It was rolled in the flour bow | picked up from the foil | Before the camera wearer sprinkles extra flour over the second chicken ball, what was done to the uncoated chi |
| 13 | DIAG | cross_event_integration | short_answer | same_skill_new_event | - | correct | Flour | flour | Before the camera wearer rolls the second chicken ball in the breadcrumbs bowl, what was the first ingredient  |
| 14 | DIAG | cross_event_integration | short_answer | coverage | - | correct | Flour | flour | What was the coating on the second chicken ball just before it was dipped in the egg? |

## L4 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | goal_conditioned_planning | single_choice | coverage | - | wrong | D | B | What is the next step the person will take to continue the task? |
| 2 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | B | B | What is the next step the person will take to continue the task? |
| 3 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | C | C | What is the next step the person will take to continue the task? |
| 4 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | B | B | What is the next step the person will take to continue the task? |
| 5 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | D | D | What is the next step the person will take to continue the task? |

## Gemini 用量

| role | calls | errors | tok_in | tok_out | tok_think |
|---|---|---|---|---|---|
| examiner | 113 | 0 | 3114977 | 70757 | 366101 |
| judge | 24 | 0 | 6322 | 1220 | 2632 |
| solver | 306 | 0 | 1298136 | 5143 | 0 |
