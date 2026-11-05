# pyramid2 run `p2_hdepicE_1023t_g4_v16_self__39`

dataset hdepic_e · videos 1 · examiner `gcp/google/gemini-3.1-pro-preview` · solver `gcp/google/gemini-4-argon` · n_per_layer 200 · seed 1023 · prompt physical-mental-draft2-hdepic-e+v16sg

**结果为 provisional**:gold = Examiner 的 proposed_reference_answer,未经人工核验;open/plan 题由 Gemini judge 判。

## 每层概览

| layer | stop | turns | scored | correct | raw acc | cluster-dedup acc | follow-up | invalid/unresolved | confirmation |
|---|---|---|---|---|---|---|---|---|---|
| L1 | STAIRCASE_COMPLETE | 12 | 9 | 7 | 0.778 | 0.778 | 0 | 3/0 | - |
| L2 | STAIRCASE_COMPLETE | 39 | 36 | 25 | 0.694 | 0.8 | 0 | 2/1 | - |
| L3 | STAIRCASE_COMPLETE | 6 | 6 | 5 | 0.833 | 0.833 | 0 | 0/0 | - |
| L4 | STAIRCASE_COMPLETE | 6 | 5 | 3 | 0.6 | 0.6 | 0 | 1/0 | - |

## 每层 × skill 诊断结论

| layer | skill | verdict | scored | correct | clusters | first-try correct | supported hypotheses | confirmation |
|---|---|---|---|---|---|---|---|---|
| L1 | spatial_near | boundary 2.0 | 1 | 1 | 1 |  | - | - |
| L1 | spatial_side | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L1 | object_recognition | boundary 3 | 2 | 2 | 2 |  | - | - |
| L1 | object_location_at_time | boundary 2.5 | 3 | 3 | 3 |  | - | - |
| L1 | object_grounding | boundary<1 | 3 | 1 | 3 |  | - | - |
| L2 | sound_action_binding | boundary<1 | 8 | 4 | 5 |  | - | - |
| L2 | object_state_change | boundary>=4 | 2 | 2 | 2 |  | - | - |
| L2 | action_temporal_order | boundary 2.75 | 12 | 9 | 5 |  | - | - |
| L2 | action_recognition | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | event_object_role | boundary>=4 | 2 | 2 | 2 |  | - | - |
| L2 | sound_anchored_spatial_near | boundary<1 | 3 | 1 | 2 |  | - | - |
| L2 | sound_anchored_spatial_side | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L2 | sound_movement_binding | boundary<1 | 3 | 1 | 3 |  | - | - |
| L3 | cross_event_integration | boundary>=4 | 5 | 4 | 5 |  | - | - |
| L3 | hidden_state_inference | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | spatial_state_integration | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | causal_prerequisite_reasoning | boundary 1.0 | 1 | 1 | 1 |  | - | - |
| L4 | goal_conditioned_planning | boundary 3 | 5 | 3 | 5 |  | - | - |

## L1 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | spatial_near | single_choice | coverage | - | correct | B | B | When the popping or cracking sound is heard as the can seal is broken, at the start of the clip, which of the  |
| 2 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | At the start of the clip, when the camera wearer carries an object over to the sink in their left hand, which  |
| 3 | DIAG | object_recognition | single_choice | same_skill_new_event | - | correct | A | A | At the start of the clip, the camera wearer puts an object down in the sink. Which object is it? |
| 4 | DIAG | object_recognition | short_answer | coverage | - | item_invalid | None | can opener | About 7 seconds into the clip, the person opens the can of chickpeas using a pull tab or can opener. At the st |
| 5 | DIAG | object_recognition | short_answer | coverage | - | item_invalid | None | can opener | About 1 second into the clip, as the person opens the can of chickpeas, what object do they readjust using bot |
| 6 | DIAG | object_recognition | short_answer | coverage | - | item_invalid | None | roll of kitchen paper | About 8 seconds into the clip, the person starts to dump the rinsed chickpeas from the colander onto paper tow |
| 7 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 4 seconds into the clip, the person dumps the rinsed chickpeas from the colander onto paper towels. At t |
| 8 | DIAG | object_location_at_time | single_choice | same_skill_new_event | - | correct | A | A | At the start of the clip, when a popping or cracking sound is heard as the can seal is broken, where is the ca |
| 9 | DIAG | object_location_at_time | single_choice | same_skill_new_event | - | correct | A | A | About 3 seconds into the clip, the sound of running water is heard. Just before this, where does the camera we |
| 10 | DIAG | object_grounding | bbox | coverage | - | correct | [0.47, 0.74, 0.69, 0.98] | 47.2, 78.8, 69.7, 100.2 | About half a second into the clip, the sound of running water splashing into the metal can is heard. In the fi |
| 11 | DIAG | object_grounding | bbox | same_skill_new_event | - | wrong | [0.0441, 0.5806, 0.7188, 0.843 | 47.4, 64.8, 69.4, 88.5 | At the start of the clip, the sound of running water splashing into the metal can is heard. In the first frame |
| 12 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.44, 0.65, 0.5, 0.74] | 45.6, 65.8, 53.2, 76.9 | At the start of the clip, a popping or cracking sound is heard as the can seal is broken. In the first frame o |

## L2 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | Which action produces the cutting sounds heard in the clip? |
| 2 | DIAG | sound_action_binding | single_choice | coverage | - | correct | B | B | Which action produces the sound of liquid pouring out of the can heard in the clip? |
| 3 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | Which action produces the continuous water sounds heard in the clip? |
| 4 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | When the person dumps the rinsed chickpeas from the colander onto paper towels, which action produces the seco |
| 5 | DIAG | sound_action_binding | single_choice | coverage | - | wrong | B | A | When the person moves the dried chickpeas from the paper towels onto a baking tray, which action produces the  |
| 6 | DIAG | sound_action_binding | single_choice | coverage | - | wrong | A | C | Which action produces the first opening or closing sound heard in the clip? |
| 7 | DIAG | sound_action_binding | single_choice | coverage | - | wrong | B | A | Which action produces the metal collision sound heard in the clip? |
| 8 | DIAG | sound_action_binding | single_choice | coverage | - | wrong | D | A | When the person dumps the rinsed chickpeas from the colander onto paper towels, which action produces the firs |
| 9 | DIAG | object_state_change | short_answer | coverage | - | correct | On the kitchen counter | on the counter | When the person picks up the can of chickpeas, where do they place it? |
| 10 | DIAG | object_state_change | short_answer | same_skill_new_event | - | correct | In the sink | In the sink | When the person puts down the can of chickpeas, where do they place it? |
| 11 | DIAG | action_temporal_order | - | request_verification | - | evidence_unresolved | None | None |  |
| 12 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | In the clip, which of the following sequences of actions is in the correct order? |
| 13 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | wrong | B | A | When the person shakes the colander to drain the excess water, what is the correct order of their movements? |
| 14 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | A | A | When the person dumps the rinsed chickpeas from the colander onto paper towels, which of the following sequenc |
| 15 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | When the person removes the loose skins from the chickpeas, what specific action do they use? |
| 16 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | A | A | When the person moves the dried chickpeas from the paper towels onto a baking tray, which of the following seq |
| 17 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | When the person handles the can of chickpeas over the sink, which of the following sequences of actions is in  |
| 18 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | When the person handles the can of chickpeas over the sink, which of the following sequences of actions is in  |
| 19 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | A | A | When the person runs water over the chickpeas in the colander, which of the following sequences of actions is  |
| 20 | DIAG | action_temporal_order | short_answer | coverage | - | correct | Rinses it under the running wa | holds it under the running wat | What does the person do with the can immediately after peeling back its metal lid? |
| 21 | DIAG | action_temporal_order | short_answer | coverage | - | wrong | Shakes the colander to drain t | Swirls the colander | What does the person do immediately after turning off the tap? |
| 22 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | A | A | When the person gently rubs or pats the chickpeas with paper towels, which of the following sequences of actio |
| 23 | DIAG | action_temporal_order | single_choice | coverage | - | wrong | C | A | When the person discards the removed skins into a pile, which of the following sequences of actions is in the  |
| 24 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | How does the person open the can of chickpeas? |
| 25 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | When the person rinses the inside of the can, how do they do it? |
| 26 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | When the person rinses the chickpeas under the running water, how do they move the colander? |
| 27 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | When the person dries the chickpeas, what specific action do they use? |
| 28 | DIAG | action_recognition | short_answer | coverage | - | correct | Places them on the counter abo | Place them on the counter | When the person handles the loose skins after removing them from the chickpeas, what do they do with them? |
| 29 | DIAG | action_recognition | short_answer | coverage | - | correct | By lifting the paper towel and | They lift the paper towel and  | When the person moves the dried chickpeas from the paper towels onto a baking tray, how do they transfer them? |
| 30 | DIAG | event_object_role | short_answer | coverage | - | correct | Can opener | Can opener | When the person opens the can of chickpeas, what tool do they use? |
| 31 | DIAG | event_object_role | short_answer | same_skill_new_event | - | correct | a white colander | The colander | When the person empties the can, what object do they pour the chickpeas into? |
| 32 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | item_invalid | None | B | When the first cutting sound is heard as the person opens the container, among the listed candidates, which ob |
| 33 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | correct | A | A | When the first cutting sound is heard as the person opens the container, which object is nearest relative to t |
| 34 | DIAG | sound_anchored_spatial_near | single_choice | same_skill_new_event | - | wrong | B | A | When the sound of liquid pouring is heard as the person tips the can, which object is nearest relative to the  |
| 35 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | item_invalid | None | B | When the metal or plastic collision sound is heard as the person opens the can of chickpeas, which object is n |
| 36 | DIAG | sound_anchored_spatial_near | single_choice | same_skill_cleaner_event | - | wrong | B | A | When the sound of liquid pouring is heard as the person tips the can, among the following objects, which is ne |
| 37 | DIAG | sound_movement_binding | single_choice | coverage | - | wrong | B | A | Which movement produces the opening or closing sound heard in the clip? |
| 38 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | correct | A | A | Which movement produces the plastic collision sound heard in the clip? |
| 39 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | wrong | C | A | When the person dumps the rinsed chickpeas from the colander onto paper towels, which movement produces the pa |

## L3 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | cross_event_integration | short_answer | coverage | - | wrong | It was opened with a manual ca | It was rinsed out with water. | What was done to the can just before the chickpeas are rinsed in the colander? |
| 2 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | What was done to the chickpeas just before they are dumped onto the paper towels? |
| 3 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | B | B | What is the moisture state of the chickpeas when their loose skins are being removed? |
| 4 | DIAG | cross_event_integration | short_answer | same_skill_new_event | - | correct | Dried with paper towels and lo | Their loose skins were removed | What was done to the chickpeas just before they are transferred to the baking tray? |
| 5 | DIAG | cross_event_integration | short_answer | same_skill_new_event | - | correct | It was opened using a manual c | It was opened. | What was done to the can before it is tipped to pour the aquafaba liquid down the sink drain? |
| 6 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | A | A | Which earlier action was necessary for the person to be able to pour liquid out of the can? |

## L4 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | goal_conditioned_planning | plan | coverage | - | correct | ['Remove any loose skins from  | 1. Remove the loose skins from | List the remaining stages, in order, to complete the task the camera wearer is doing. |
| 2 | DIAG | goal_conditioned_planning | plan | same_skill_new_event | - | wrong | ['Finish drying the chickpeas  | 1. Move the chickpeas to a bak | List the remaining stages, in order, to complete the task the camera wearer is doing. |
| 3 | DIAG | goal_conditioned_planning | single_choice | coverage | - | item_invalid | None | B | What is the next stage to complete the task the camera wearer is doing? |
| 4 | DIAG | goal_conditioned_planning | single_choice | same_event_new_format | - | correct | B | B | What is the next stage to complete the task the camera wearer is doing? |
| 5 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | B | B | What is the next stage to complete the task the camera wearer is doing? |
| 6 | DIAG | goal_conditioned_planning | plan | coverage | - | wrong | ['Place a towel on the baking  | 1. Move the chickpeas onto pap | List the remaining stages, in order, to complete the task the camera wearer is doing. |

## Gemini 用量

| role | calls | errors | tok_in | tok_out | tok_think |
|---|---|---|---|---|---|
| examiner | 86 | 0 | 2292073 | 54913 | 353605 |
| judge | 20 | 0 | 8999 | 2005 | 6654 |
| scope | 1 | 0 | 1648 | 2829 | 1721 |
| solver | 168 | 0 | 705498 | 2986 | 0 |
