# pyramid2 run `p2_hdepicE_1023t_g4_v16_goldlive__54`

dataset hdepic_e · videos 1 · examiner `gcp/google/gemini-3.1-pro-preview` · solver `gcp/google/gemini-4-argon` · n_per_layer 200 · seed 1023 · prompt physical-mental-draft2-hdepic-e+v16sg

**结果为 provisional**:gold = Examiner 的 proposed_reference_answer,未经人工核验;open/plan 题由 Gemini judge 判。

## 每层概览

| layer | stop | turns | scored | correct | raw acc | cluster-dedup acc | follow-up | invalid/unresolved | confirmation |
|---|---|---|---|---|---|---|---|---|---|
| L1 | STAIRCASE_COMPLETE | 14 | 14 | 9 | 0.643 | 0.615 | 0 | 0/0 | - |
| L2 | STAIRCASE_COMPLETE | 39 | 36 | 28 | 0.778 | 0.812 | 0 | 0/3 | - |
| L3 | STAIRCASE_COMPLETE | 9 | 9 | 7 | 0.778 | 0.778 | 0 | 0/0 | - |
| L4 | STAIRCASE_COMPLETE | 7 | 7 | 5 | 0.714 | 0.714 | 0 | 0/0 | - |

## 每层 × skill 诊断结论

| layer | skill | verdict | scored | correct | clusters | first-try correct | supported hypotheses | confirmation |
|---|---|---|---|---|---|---|---|---|
| L1 | spatial_near | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L1 | spatial_side | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L1 | object_recognition | boundary 2 | 6 | 4 | 6 |  | - | - |
| L1 | object_location_at_time | boundary>=4 | 5 | 5 | 4 |  | - | - |
| L1 | object_grounding | boundary<1 | 3 | 0 | 3 |  | - | - |
| L2 | sound_action_binding | boundary<1 | 4 | 1 | 4 |  | - | - |
| L2 | object_state_change | boundary>=4 | 6 | 6 | 4 |  | - | - |
| L2 | action_temporal_order | boundary 3.5 | 8 | 7 | 8 |  | - | - |
| L2 | action_recognition | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | event_object_role | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | sound_anchored_spatial_near | boundary 2.0 | 1 | 1 | 1 |  | - | - |
| L2 | sound_anchored_spatial_side | boundary<1 | 2 | 0 | 1 |  | - | - |
| L2 | sound_movement_binding | boundary<1 | 3 | 1 | 2 |  | - | - |
| L3 | cross_event_integration | boundary 3 | 9 | 7 | 9 |  | - | - |
| L3 | hidden_state_inference | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | spatial_state_integration | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | causal_prerequisite_reasoning | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L4 | goal_conditioned_planning | boundary 2 | 7 | 5 | 7 |  | - | - |

## L1 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | object_recognition | single_choice | coverage | - | correct | B | B | About 6 seconds into the clip, the camera wearer examines an object with both hands. What object are they exam |
| 2 | DIAG | object_recognition | single_choice | same_skill_new_event | - | correct | B | B | About 2 seconds into the clip, the camera wearer tips an object to pour out water into the sink. What object a |
| 3 | DIAG | object_recognition | single_choice | coverage | - | wrong | C | A | At the start of the clip (about 0 seconds in), the camera wearer picks up an object from the counter surface w |
| 4 | DIAG | object_recognition | single_choice | same_skill_new_event | - | wrong | D | B | About 6 seconds into the clip, the camera wearer picks up an object from the counter surface with their left h |
| 5 | DIAG | object_recognition | single_choice | coverage | - | correct | C | C | About 2 seconds into the clip, the camera wearer retrieves an object from a rack using their right hand. What  |
| 6 | DIAG | object_recognition | single_choice | same_skill_new_event | - | correct | A | A | About 8 seconds into the clip, the camera wearer places chopped pieces into a container using both hands. What |
| 7 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 9 seconds into the clip, the ginger is placed onto the digital scale. Earlier, about 0 seconds into the  |
| 8 | DIAG | object_location_at_time | single_choice | same_skill_new_event | - | correct | A | A | About 8 seconds into the clip, the camera wearer places the knife down. Where is it placed? |
| 9 | DIAG | object_location_at_time | single_choice | coverage | - | correct | C | C | About 9 seconds into the clip, the camera wearer places a piece of ginger down. Where do they place it? |
| 10 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 9 seconds into the clip, the camera wearer places the saucepan down. Where do they place it? |
| 11 | DIAG | object_location_at_time | short_answer | coverage | - | correct | On the cutting board | on the chopping board | About 9 seconds into the clip, the camera wearer places the washed piece of ginger down to be chopped. Where d |
| 12 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.56, 0.65, 0.67, 0.79] | 63.9, 73.2, 73.3, 81.7 | At the start of the clip (about 0 seconds in), the ginger is placed onto the digital scale. What is the boundi |
| 13 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.011460000000000001, 0.71875 | 20.7, 71.6, 44.8, 88.0 | At the start of the clip (about 0 seconds in), the camera wearer places the saucepan on the burner. What is th |
| 14 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.326, 0.615, 0.424, 0.795] | 23.4, 68.7, 40.0, 84.6 | At the start of the clip (about 0 seconds in), the camera wearer picks up the chopping board. What is the boun |

## L2 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | sound_action_binding | single_choice | coverage | - | wrong | A | B | At the moment the metallic or wooden collision sound is heard, among the following objects, which one is farth |
| 2 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | Which action produces the sound of running water heard in the clip? |
| 3 | DIAG | sound_action_binding | - | request_verification | - | evidence_unresolved | None | None |  |
| 4 | DIAG | sound_action_binding | single_choice | coverage | - | wrong | C | B | Which action produces the opening or closing sound heard in the clip? |
| 5 | DIAG | sound_action_binding | single_choice | coverage | - | wrong | B | A | Which action produces the metallic or wooden collision sound heard in the clip? |
| 6 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the piece of ginger is placed down from the right hand after being broken in half, where is it placed? |
| 7 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the saucepan is placed down after being filled with water, where is it placed? |
| 8 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the knife is placed down from the right hand, where is it placed? |
| 9 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the chopped ginger is placed down from the hands, where is it placed? |
| 10 | DIAG | object_state_change | short_answer | coverage | - | correct | On the weighing scale | on the weighing scale | When the piece of ginger is placed down from the right hand after being broken in half, where is it placed? |
| 11 | DIAG | object_state_change | short_answer | same_event_new_format | - | correct | On the hob | On the hob | When the saucepan is placed down after being filled with water, where is it placed? |
| 12 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | What does the camera wearer do immediately after breaking the ginger into two halves? |
| 13 | DIAG | action_temporal_order | single_choice | coverage | - | correct | C | C | What does the camera wearer do immediately after pouring the water out of the saucepan into the sink? |
| 14 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | What does the camera wearer do immediately after pouring the flower pieces from the pack onto the weighing sca |
| 15 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | What does the camera wearer do immediately after picking up more hibiscus flowers from the counter surface? |
| 16 | DIAG | action_temporal_order | short_answer | coverage | - | correct | They place the knife on the cu | places the knife on the cuttin | What does the camera wearer do immediately after placing the cutting board on the counter? |
| 17 | DIAG | action_temporal_order | short_answer | coverage | - | wrong | Picks up more hibiscus flowers | Lift the ginger from the scale | What does the camera wearer do immediately after pouring the first handful of hibiscus flowers into the saucep |
| 18 | DIAG | action_temporal_order | single_choice | coverage | - | correct | B | B | What does the camera wearer do immediately after placing the washed piece of ginger back on the chopping board |
| 19 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | What does the camera wearer do immediately after reaching into the plastic bag with their right hand? |
| 20 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | What does the camera wearer do with the piece of ginger in their right hand after breaking the ginger into two |
| 21 | DIAG | action_recognition | single_choice | coverage | - | correct | B | B | When the sound of running water is heard, what does the camera wearer do with the saucepan? |
| 22 | DIAG | action_recognition | single_choice | coverage | - | correct | C | C | What does the camera wearer do to open the pack of hibiscus flower after trying to pull it apart with both han |
| 23 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | What does the camera wearer do with the hibiscus flowers after picking them up from the counter surface? |
| 24 | DIAG | action_recognition | short_answer | coverage | - | correct | Places it on the counter | Places it on the counter | What does the camera wearer do with the cutting board after picking it up from the draining rack? |
| 25 | DIAG | action_recognition | short_answer | coverage | - | correct | puts them into the saucepan | Places them in the saucepan | What does the camera wearer do with the hibiscus flowers after scooping them up from the counter surface? |
| 26 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | When the camera wearer places an object onto the weighing scale, what object is being placed? |
| 27 | DIAG | event_object_role | single_choice | coverage | - | correct | B | B | When the camera wearer fills an object with water from the running tap, which object is being filled? |
| 28 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | When the camera wearer pours the hibiscus flowers out of the package, what do they pour them onto? |
| 29 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | When the camera wearer clears the hibiscus flowers and ginger using both hands, what object are they removed f |
| 30 | DIAG | event_object_role | short_answer | coverage | - | correct | The cutting board | The cutting board | When the camera wearer places the knife down, what do they place it on? |
| 31 | DIAG | event_object_role | short_answer | coverage | - | correct | In the saucepan | in the saucepan | Where does the camera wearer place the hibiscus flowers using their right hand? |
| 32 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | correct | C | C | At the moment the opening or closing sound is heard, among the following objects, which one is nearest to the  |
| 33 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | wrong | A | B | At the moment the metallic or wooden collision sound is heard, among the following objects, which one is farth |
| 34 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | wrong | A | B | At the moment the metallic or wooden collision sound is heard, from the camera wearer's own viewpoint at that  |
| 35 | DIAG | sound_movement_binding | - | request_verification | - | evidence_unresolved | None | None |  |
| 36 | DIAG | sound_movement_binding | - | request_verification | - | evidence_unresolved | None | None |  |
| 37 | DIAG | sound_movement_binding | single_choice | coverage | - | wrong | A | B | Which movement produces the metallic or wooden collision sound heard in the clip? |
| 38 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | Which movement produces the cutting or chopping sound heard in the clip? |
| 39 | DIAG | sound_movement_binding | single_choice | coverage | - | wrong | B | A | Which movement produces the sound of plastic hitting a surface heard in the clip? |

## L3 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | What was done to the hibiscus flowers before they were removed from the scale? |
| 2 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | What ingredient is already in the saucepan when the chopped ginger is added? |
| 3 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | What was added to the saucepan right before the additional hibiscus flowers from the plastic bag? |
| 4 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | What solid ingredients are present in the saucepan when the second batch of water is poured in? |
| 5 | DIAG | cross_event_integration | short_answer | coverage | - | wrong | The contents were stirred and  | a second batch was added | What was done to the saucepan before the third batch of water is added to it? |
| 6 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | What was done to the hibiscus flowers before they are placed back onto the scale? |
| 7 | DIAG | cross_event_integration | single_choice | coverage | - | wrong | B | A | Before the hibiscus flowers are removed from the scale, how was their package opened? |
| 8 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | What was done to the package of hibiscus flowers before the flowers are placed back onto the scale? |
| 9 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | What was added to the saucepan right before the additional hibiscus flowers from the plastic bag? |

## L4 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | B | B | What is the next step the person will take for the task they are doing? |
| 2 | DIAG | goal_conditioned_planning | single_choice | coverage | - | wrong | D | B | What is the next step the person will take for the task they are doing? |
| 3 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | C | C | What is the next step the person will take for the task they are doing? |
| 4 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | B | B | What is the next step the person will take for the task they are doing? |
| 5 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | B | B | What is the next step the person will take for the task they are doing? |
| 6 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | B | B | What is the next step the person will take for the task they are doing? |
| 7 | DIAG | goal_conditioned_planning | plan | coverage | - | wrong | ['Pour water into the saucepan | 1. Pour a second batch of wate | List the remaining stages, in order, for the task the camera wearer is doing. |

## Gemini 用量

| role | calls | errors | tok_in | tok_out | tok_think |
|---|---|---|---|---|---|
| examiner | 71 | 0 | 1737755 | 41783 | 236114 |
| judge | 13 | 0 | 4669 | 941 | 2206 |
| solver | 198 | 0 | 993024 | 3289 | 0 |
