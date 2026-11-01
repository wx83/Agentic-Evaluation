# pyramid2 run `p2_hdepicE_1023t_g4_v16_self__54`

dataset hdepic_e · videos 1 · examiner `gcp/google/gemini-3.1-pro-preview` · solver `gcp/google/gemini-4-argon` · n_per_layer 200 · seed 1023 · prompt physical-mental-draft2-hdepic-e+v16sg

**结果为 provisional**:gold = Examiner 的 proposed_reference_answer,未经人工核验;open/plan 题由 Gemini judge 判。

## 每层概览

| layer | stop | turns | scored | correct | raw acc | cluster-dedup acc | follow-up | invalid/unresolved | confirmation |
|---|---|---|---|---|---|---|---|---|---|
| L1 | STAIRCASE_COMPLETE | 16 | 16 | 12 | 0.75 | 0.733 | 0 | 0/0 | - |
| L2 | STAIRCASE_COMPLETE | 45 | 45 | 37 | 0.822 | 0.8 | 0 | 0/0 | - |
| L3 | STAIRCASE_COMPLETE | 6 | 6 | 6 | 1.0 | 1.0 | 0 | 0/0 | - |
| L4 | STAIRCASE_COMPLETE | 5 | 5 | 2 | 0.4 | 0.4 | 0 | 0/0 | - |

## 每层 × skill 诊断结论

| layer | skill | verdict | scored | correct | clusters | first-try correct | supported hypotheses | confirmation |
|---|---|---|---|---|---|---|---|---|
| L1 | spatial_near | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L1 | spatial_side | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L1 | object_recognition | boundary 3.5 | 8 | 7 | 8 |  | - | - |
| L1 | object_location_at_time | boundary>=4 | 5 | 5 | 4 |  | - | - |
| L1 | object_grounding | boundary<1 | 3 | 0 | 3 |  | - | - |
| L2 | sound_action_binding | boundary<1 | 5 | 2 | 5 |  | - | - |
| L2 | object_state_change | boundary>=4 | 6 | 6 | 4 |  | - | - |
| L2 | action_temporal_order | boundary 3.5 | 8 | 7 | 8 |  | - | - |
| L2 | action_recognition | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | event_object_role | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | sound_anchored_spatial_near | boundary 2.0 | 1 | 1 | 1 |  | - | - |
| L2 | sound_anchored_spatial_side | boundary<1 | 2 | 0 | 1 |  | - | - |
| L2 | sound_movement_binding | boundary>=4 | 11 | 9 | 4 |  | - | - |
| L3 | cross_event_integration | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L3 | hidden_state_inference | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | spatial_state_integration | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | causal_prerequisite_reasoning | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L4 | goal_conditioned_planning | boundary<1 | 5 | 2 | 5 |  | - | - |

## L1 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 8 seconds into the clip, the camera wearer breaks an object into two halves using both hands. What objec |
| 2 | DIAG | object_recognition | single_choice | same_skill_new_event | - | correct | A | A | About 8 seconds into the clip, the camera wearer places an object on the burner using their right hand. What o |
| 3 | DIAG | object_recognition | single_choice | same_skill_new_event | - | correct | C | C | About 1 second into the clip, the camera wearer pulls the top part of an object with both hands to try to open |
| 4 | DIAG | object_recognition | single_choice | coverage | - | correct | C | C | About 3 seconds into the clip, the camera wearer picks up an object from the counter surface using their right |
| 5 | DIAG | object_recognition | short_answer | same_skill_new_event | - | correct | cutting board | chop board | About 7 seconds into the clip, the camera wearer places an object on the counter surface using their left hand |
| 6 | DIAG | object_recognition | short_answer | coverage | - | wrong | hibiscus flowers | ginger | About 2 seconds into the clip, in the event where the weighed hibiscus flowers are poured into the saucepan, t |
| 7 | DIAG | object_recognition | single_choice | coverage | - | correct | C | C | About 1 second into the clip, the camera wearer washes an object under the running tap water with both hands.  |
| 8 | DIAG | object_recognition | single_choice | coverage | - | correct | C | C | About 4 seconds into the clip, in the event where a second batch of water is poured into the saucepan, the cam |
| 9 | DIAG | object_location_at_time | single_choice | coverage | - | correct | C | C | At the start of the clip, the camera wearer moves the bag of ginger. Where is the bag of ginger placed? |
| 10 | DIAG | object_location_at_time | single_choice | same_skill_new_event | - | correct | A | A | About 8 seconds into the clip, the camera wearer places the knife. Where is the knife placed? |
| 11 | DIAG | object_location_at_time | single_choice | same_skill_new_event | - | correct | A | A | About 5 seconds into the clip, in the event where the ginger is placed onto the digital scale, the camera wear |
| 12 | DIAG | object_location_at_time | single_choice | same_skill_new_event | - | correct | A | A | About 1 second into the clip, in the event where water is heard running from the tap into the saucepan, the ca |
| 13 | DIAG | object_location_at_time | short_answer | same_skill_new_event | - | correct | on the cutting board | chopping board | About 9 seconds into the clip, in the event where chopping sounds are heard as the knife cuts the ginger, the  |
| 14 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.55, 0.67, 0.68, 0.8] | 63.9, 73.2, 73.3, 81.7 | What is the bounding box of the ginger root in the first frame of the clip? |
| 15 | DIAG | object_grounding | bbox | same_skill_new_event | - | wrong | [0.01, 0.718, 0.027, 0.901] | 20.7, 71.6, 44.8, 88.0 | What is the bounding box of the saucepan in the first frame of the clip? |
| 16 | DIAG | object_grounding | bbox | same_skill_new_event | - | wrong | [0.292, 0.608, 0.42, 0.816] | 23.4, 68.7, 40.0, 84.6 | What is the bounding box of the chopping board in the first frame of the clip? |

## L2 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | Which action produces the plastic collision sound heard in the clip? |
| 2 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | wrong | C | A | Which action produces the ceramic collision sound heard in the clip? |
| 3 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | Which action produces the metal/wood collision sound heard in the clip? |
| 4 | DIAG | sound_action_binding | single_choice | coverage | - | wrong | D | A | Which action produces the sound of something being opened or closed heard in the clip? |
| 5 | DIAG | sound_action_binding | single_choice | coverage | - | wrong | A | C | Which action produces the metal/wood collision sound heard in the clip? |
| 6 | DIAG | object_state_change | single_choice | coverage | - | correct | B | B | When the piece of ginger is placed down, where is it put? |
| 7 | DIAG | object_state_change | single_choice | coverage | - | correct | B | B | When the saucepan is moved away from the sink, where is it placed? |
| 8 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the knife is placed down, where is it put? |
| 9 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the chopped ginger is gathered from the chopping board, where is it placed? |
| 10 | DIAG | object_state_change | short_answer | coverage | - | correct | On the digital scale | on the weighing scale | When the ginger is placed down, where is it put? |
| 11 | DIAG | object_state_change | short_answer | same_event_new_format | - | correct | On the burner | On the hob | When the saucepan is moved away from the sink, where is it placed? |
| 12 | DIAG | action_temporal_order | single_choice | coverage | - | correct | C | C | During the task the camera wearer is doing, which of these actions happens immediately before they place the g |
| 13 | DIAG | action_temporal_order | single_choice | coverage | - | correct | B | B | During the task the camera wearer is doing, which of these actions happens immediately before they fill the sa |
| 14 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, which of these actions happens immediately before they place the k |
| 15 | DIAG | action_temporal_order | single_choice | coverage | - | correct | B | B | During the task the camera wearer is doing, which of these actions happens immediately before they pick up mor |
| 16 | DIAG | action_temporal_order | short_answer | coverage | - | correct | Places the knife on the choppi | Placing the knife on the chopp | During the task the camera wearer is doing, what action happens immediately after they place the chopping boar |
| 17 | DIAG | action_temporal_order | short_answer | coverage | - | wrong | Residual hibiscus pieces on th | Lifts the ginger from the scal | During the task the camera wearer is doing, what action happens immediately after the weighed hibiscus flowers |
| 18 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, which of these actions happens immediately after they turn off the |
| 19 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, which of these actions happens immediately after they reach into t |
| 20 | DIAG | action_recognition | single_choice | coverage | - | correct | B | B | During the task the camera wearer is doing, which of the following actions do they perform with the ginger in  |
| 21 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | B | B | During the task the camera wearer is doing, which of the following actions do they perform with the saucepan i |
| 22 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | B | B | During the task the camera wearer is doing, how do they transfer the hibiscus flowers from the package to the  |
| 23 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, which of the following actions do they perform with the hibiscus f |
| 24 | DIAG | action_recognition | short_answer | same_skill_new_event | - | correct | Picks it up from the dish rack | Places it on the counter | During the task the camera wearer is doing, what do they do with the chopping board in the clip? |
| 25 | DIAG | action_recognition | short_answer | same_skill_new_event | - | correct | Transfer them from the scale a | Places them in the saucepan | During the task the camera wearer is doing, what do they do with the hibiscus flowers in the clip? |
| 26 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, what do they place the ginger onto? |
| 27 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, what do they rinse under the running tap in the clip? |
| 28 | DIAG | event_object_role | single_choice | coverage | - | correct | B | B | During the task the camera wearer is doing, what do they place the hibiscus flowers onto? |
| 29 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, what do they remove the hibiscus flowers and ginger from? |
| 30 | DIAG | event_object_role | short_answer | coverage | - | correct | the counter | The kitchen counter | During the task the camera wearer is doing, what do they place the chopping board onto in the clip? |
| 31 | DIAG | event_object_role | short_answer | coverage | - | correct | a saucepan | The saucepan | During the task the camera wearer is doing, what do they place the weighed hibiscus flowers into? |
| 32 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | correct | B | B | During the task the camera wearer is doing, at the moment the sound of something being opened or closed is hea |
| 33 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | wrong | D | A | During the task the camera wearer is doing, at the moment the metal or wood collision sound is heard, which of |
| 34 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | wrong | A | B | During the task the camera wearer is doing, at the moment the metal or wood collision sound is heard, which of |
| 35 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, which object's movement produces the sound of a plastic object hit |
| 36 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | wrong | B | A | During the task the camera wearer is doing, which movement produces the sound of an object hitting a ceramic s |
| 37 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | wrong | B | A | During the task the camera wearer is doing, which object's movement produces the plastic collision sounds hear |
| 38 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, which object's movement produces the cutting or chopping sounds he |
| 39 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, which object's movement produces the sound of something being open |
| 40 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, which object's movement produces the sound of a wooden or metal ob |
| 41 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | correct | B | B | During the task the camera wearer is doing, which movement produces the water sounds heard in the clip? |
| 42 | DIAG | sound_movement_binding | single_choice | same_event_new_format | - | correct | A | A | During the task the camera wearer is doing, which movement produces the sound of something being opened or clo |
| 43 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, which movement produces the water sounds heard in the clip? |
| 44 | DIAG | sound_movement_binding | short_answer | coverage | - | correct | placing the digital scale onto | Placing the weighing scale on  | During the task the camera wearer is doing, what movement produces the plastic collision sound heard before th |
| 45 | DIAG | sound_movement_binding | short_answer | coverage | - | correct | filling the saucepan with wate | filling the saucepan with wate | During the task the camera wearer is doing, what movement produces the water sounds heard in the clip? |

## L3 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | cross_event_integration | single_choice | coverage | - | correct | C | C | What happened to the hibiscus flowers before they were removed from the scale? |
| 2 | DIAG | cross_event_integration | single_choice | coverage | - | correct | B | B | When the chopped ginger is added to the saucepan, what ingredient is already in it? |
| 3 | DIAG | cross_event_integration | single_choice | coverage | - | correct | B | B | What was added to the saucepan right before the additional hibiscus flowers from the plastic bag? |
| 4 | DIAG | cross_event_integration | single_choice | coverage | - | correct | C | C | When the second batch of water is poured into the saucepan, what dry ingredients are already in it? |
| 5 | DIAG | cross_event_integration | short_answer | coverage | - | correct | Water from the tap | water | When the saucepan is placed under the running tap for the second time in the clip, what was added to it the fi |
| 6 | DIAG | cross_event_integration | short_answer | coverage | - | correct | Taken out of the package and p | They were weighed on the scale | When the hibiscus flowers are placed onto the scale in the later part of the clip, what had already been done  |

## L4 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | B | B | What is the next step the camera wearer will take to continue the task? |
| 2 | DIAG | goal_conditioned_planning | single_choice | coverage | - | wrong | D | B | What is the next step the camera wearer will take to continue the task? |
| 3 | DIAG | goal_conditioned_planning | single_choice | coverage | - | wrong | C | B | What is the next step the camera wearer will take to continue the task? |
| 4 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | C | C | What is the next step the camera wearer will take to continue the task? |
| 5 | DIAG | goal_conditioned_planning | single_choice | coverage | - | wrong | B | C | What is the next step the camera wearer will take to continue the task? |

## Gemini 用量

| role | calls | errors | tok_in | tok_out | tok_think |
|---|---|---|---|---|---|
| examiner | 79 | 0 | 1904647 | 48184 | 247026 |
| judge | 23 | 0 | 6351 | 1181 | 3000 |
| scope | 1 | 0 | 1713 | 3153 | 3517 |
| solver | 216 | 0 | 855174 | 3622 | 0 |
