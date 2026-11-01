# pyramid2 run `p2_hdepicE_1023t_g4_v16_goldlive__07`

dataset hdepic_e · videos 1 · examiner `gcp/google/gemini-3.1-pro-preview` · solver `gcp/google/gemini-4-argon` · n_per_layer 200 · seed 1023 · prompt physical-mental-draft2-hdepic-e+v16sg

**结果为 provisional**:gold = Examiner 的 proposed_reference_answer,未经人工核验;open/plan 题由 Gemini judge 判。

## 每层概览

| layer | stop | turns | scored | correct | raw acc | cluster-dedup acc | follow-up | invalid/unresolved | confirmation |
|---|---|---|---|---|---|---|---|---|---|
| L1 | STAIRCASE_COMPLETE | 35 | 30 | 22 | 0.733 | 0.704 | 0 | 0/5 | - |
| L2 | STAIRCASE_COMPLETE | 43 | 41 | 33 | 0.805 | 0.821 | 0 | 0/2 | - |
| L3 | STAIRCASE_COMPLETE | 12 | 12 | 10 | 0.833 | 0.833 | 0 | 0/0 | - |
| L4 | STAIRCASE_COMPLETE | 5 | 5 | 4 | 0.8 | 0.8 | 0 | 0/0 | - |

## 每层 × skill 诊断结论

| layer | skill | verdict | scored | correct | clusters | first-try correct | supported hypotheses | confirmation |
|---|---|---|---|---|---|---|---|---|
| L1 | spatial_near | boundary 2 | 7 | 5 | 5 |  | - | - |
| L1 | spatial_side | boundary 2.5 | 6 | 5 | 5 |  | - | - |
| L1 | object_recognition | boundary 3.5 | 8 | 7 | 8 |  | - | - |
| L1 | object_location_at_time | boundary 2.5 | 4 | 3 | 4 |  | - | - |
| L1 | object_grounding | boundary 1.5 | 5 | 2 | 5 |  | - | - |
| L2 | sound_action_binding | boundary 2.5 | 5 | 4 | 5 |  | - | - |
| L2 | object_state_change | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | action_temporal_order | boundary<1 | 3 | 0 | 3 |  | - | - |
| L2 | action_recognition | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | event_object_role | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | sound_anchored_spatial_near | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L2 | sound_anchored_spatial_side | boundary 2 | 6 | 4 | 4 |  | - | - |
| L2 | sound_movement_binding | boundary 2.5 | 9 | 7 | 9 |  | - | - |
| L3 | cross_event_integration | boundary 3.5 | 8 | 7 | 8 |  | - | - |
| L3 | hidden_state_inference | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | spatial_state_integration | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | causal_prerequisite_reasoning | boundary 1.75 | 4 | 3 | 4 |  | - | - |
| L4 | goal_conditioned_planning | boundary 2.5 | 5 | 4 | 5 |  | - | - |

## L1 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | spatial_near | single_choice | coverage | - | correct | C | C | About 5 seconds into the clip, the person peels an onion. At the moment about 8 seconds into the clip, which o |
| 2 | DIAG | spatial_near | single_choice | coverage | - | correct | B | B | At the start of the clip, the ingredients are placed on the tabletop. At the moment about 10 seconds into the  |
| 3 | DIAG | spatial_near | single_choice | coverage | - | wrong | A | C | About 0 seconds into the clip, the crushed garlic is added to the mixer jar. At the moment about 4 seconds int |
| 4 | DIAG | spatial_near | single_choice | coverage | - | correct | A | A | About 11 seconds into the clip, a knife is placed on the counter. At the moment about 11 seconds into the clip |
| 5 | DIAG | spatial_near | single_choice | coverage | - | wrong | C | A | About 5 seconds into the clip, the blender is turned on. At the moment about 1 second into the clip, which of  |
| 6 | DIAG | spatial_near | single_choice | coverage | - | correct | C | C | About 2 seconds into the clip, the ingredients are placed on the tabletop. At the end of the clip, which of th |
| 7 | DIAG | spatial_near | single_choice | coverage | - | correct | A | A | About 11 seconds into the clip, a knife is placed on the counter. At the end of the clip, which of the followi |
| 8 | DIAG | spatial_side | single_choice | coverage | - | correct | B | B | About 5 seconds into the clip, the person peels an onion. At the moment about 8 seconds into the clip, from th |
| 9 | DIAG | spatial_side | single_choice | coverage | - | correct | B | B | About 7 seconds into the clip, the chopped ingredients are transferred into a bowl. At that moment, from the c |
| 10 | DIAG | spatial_side | single_choice | coverage | - | correct | C | C | About 4 seconds into the clip, tomatoes are placed on the scale. At that moment, from the camera wearer's own  |
| 11 | DIAG | spatial_side | single_choice | coverage | - | wrong | D | C | About 10 seconds into the clip, a knife is placed on the counter. At that moment, from the camera wearer's own |
| 12 | DIAG | spatial_side | single_choice | coverage | - | correct | B | B | About 2 seconds into the clip, tomatoes are placed on the scale. At that moment, from the camera wearer's own  |
| 13 | DIAG | spatial_side | single_choice | coverage | - | correct | D | D | About 5 seconds into the clip, the person picks up a knife. At that moment, from the camera wearer's own viewp |
| 14 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 5 seconds into the clip, the ingredients are placed on the tabletop. At that moment, which of the follow |
| 15 | DIAG | object_recognition | single_choice | coverage | - | correct | B | B | About 10 seconds into the clip, the person places an object on the tabletop. At that moment, which of the foll |
| 16 | DIAG | object_recognition | - | request_verification | - | evidence_unresolved | None | None |  |
| 17 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 7 seconds into the clip, the person picks up an object from the table top. At that moment, which of the  |
| 18 | DIAG | object_recognition | single_choice | coverage | - | correct | B | B | At the start of the clip, a chopping sound is heard as the knife hits the board. At that moment, which of the  |
| 19 | DIAG | object_recognition | - | request_verification | - | evidence_unresolved | None | None |  |
| 20 | DIAG | object_recognition | short_answer | coverage | - | correct | a knife | knife | About 8 seconds into the clip, more tomatoes are sliced and placed into the mixer jar. At that moment, what ob |
| 21 | DIAG | object_recognition | short_answer | coverage | - | wrong | the sliced tomatoes | a knife | About 0 seconds into the clip, more tomatoes are sliced and placed into the mixer jar. At that moment, what ob |
| 22 | DIAG | object_recognition | single_choice | coverage | - | correct | C | C | About 0 seconds into the clip, the person chops the remaining onions into larger bits. At the moment about 1 s |
| 23 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 5 seconds into the clip, the person uses a knife to cut a protruding piece. At that moment, which of the |
| 24 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 2 seconds into the clip, the ingredients are placed down. At that moment, where is the jar of ginger pas |
| 25 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 10 seconds into the clip, a chopping board is placed on the counter. At the moment about 5 seconds into  |
| 26 | DIAG | object_location_at_time | single_choice | coverage | - | wrong | B | A | About 5 seconds into the clip, the person peels an onion. At the moment about 4 seconds into the clip, where i |
| 27 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 4 seconds into the clip, the person peels the additional onions. At the moment about 9 seconds into the  |
| 28 | DIAG | object_location_at_time | - | request_verification | - | evidence_unresolved | None | None |  |
| 29 | DIAG | object_location_at_time | - | request_verification | - | evidence_unresolved | None | None |  |
| 30 | DIAG | object_location_at_time | - | request_verification | - | evidence_unresolved | None | None |  |
| 31 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.423, 0.645, 0.513, 0.767] | 51.1, 69.6, 63.6, 82.7 | At the start of the clip, the ingredients are placed on the tabletop. In the first frame of the clip, what is  |
| 32 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.472, 0.608, 0.639, 0.983] | 47.4, 59.0, 57.4, 81.2 | At the start of the clip, a chopping board is placed on the counter. In the first frame of the clip, what is t |
| 33 | DIAG | object_grounding | bbox | coverage | - | correct | [0.41, 0.667, 0.691, 0.951] | 46.7, 67.2, 77.6, 95.9 | At the start of the clip, a chopping board is placed on the counter. In the first frame of the clip, what is t |
| 34 | DIAG | object_grounding | bbox | coverage | - | correct | [0.56, 0.51, 0.69, 0.73] | 56.8, 55.6, 71.8, 69.9 | At the start of the clip, the person picks up the knife. In the first frame of the clip, what is the bounding  |
| 35 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.52, 0.48, 0.72, 0.74] | 55.9, 58.8, 67.0, 75.2 | At the start of the clip, the person peels an onion. In the first frame of the clip, what is the bounding box  |

## L2 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | sound_action_binding | single_choice | coverage | - | correct | B | B | When the ingredients are placed on the tabletop, a sliding sound is heard. Which action produces this sound? |
| 2 | DIAG | sound_action_binding | single_choice | coverage | - | correct | C | C | During the clip, a sound of ceramic clinking is heard. Which action produces this sound? |
| 3 | DIAG | sound_action_binding | single_choice | coverage | - | wrong | C | A | While the person is peeling and preparing the onion, a sound of metal against wood is heard. Which action prod |
| 4 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | Before the person peels the additional onions, a sound of metal hitting wood is heard. Which action produces t |
| 5 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | During the clip, a sound of a knife hitting a board is heard. Which action produces this sound? |
| 6 | DIAG | object_state_change | single_choice | coverage | - | correct | B | B | When the person takes ingredients out of the refrigerator, from which part of the refrigerator are the green c |
| 7 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the person retrieves the knife, where is it placed? |
| 8 | DIAG | object_state_change | single_choice | coverage | - | correct | B | B | When the person picks up a piece of onion to start peeling it, where is it picked up from? |
| 9 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | After the person picks up a piece of onion from the chopping board and peels it, where is it placed? |
| 10 | DIAG | object_state_change | short_answer | coverage | - | correct | Places them on the weighing sc | places them on the weighing ba | What does the person do with the tomatoes after picking them up from the chopping board for the first time in  |
| 11 | DIAG | object_state_change | short_answer | coverage | - | correct | In the blender jar | In the jar | When the person picks up the sliced tomatoes, where are they placed? |
| 12 | DIAG | action_temporal_order | single_choice | coverage | - | wrong | D | A | During the clip, the person places several items on the tabletop. In what order are the following items placed |
| 13 | DIAG | action_temporal_order | single_choice | coverage | - | wrong | B | A | During the clip, the person places several tools down. In what order are the following tools placed? |
| 14 | DIAG | action_temporal_order | single_choice | coverage | - | wrong | B | A | During the clip, the person peels an onion. In what order do the following actions occur? |
| 15 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | When the person interacts with the green chillies at the refrigerator, what action do they perform? |
| 16 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the clip, what action does the person perform involving the chopping board and the tabletop? |
| 17 | DIAG | action_recognition | single_choice | coverage | - | correct | B | B | During the clip, what action does the person perform on the piece of onion immediately after picking it up fro |
| 18 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the clip, what action does the person perform to prepare the onion without using a knife? |
| 19 | DIAG | action_recognition | short_answer | coverage | - | correct | chops the onion into small pie | Chops the onion | During the clip, what action does the person perform immediately after picking up the knife from the chopping  |
| 20 | DIAG | action_recognition | short_answer | coverage | - | correct | chops it with the knife | chops the onion | During the clip, what action does the person perform on the piece of onion immediately after placing it on the |
| 21 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | When the ingredients are placed on the tabletop, which of the following items is among those placed? |
| 22 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | During the clip, the person places a knife down. What is the knife placed on? |
| 23 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | During the clip, the person peels an ingredient. Which ingredient is being peeled? |
| 24 | DIAG | event_object_role | single_choice | coverage | - | correct | B | B | During the clip, the person places an ingredient on the weighing scale. Which ingredient is placed? |
| 25 | DIAG | event_object_role | short_answer | coverage | - | correct | onion | onion | During the clip, what ingredient does the person chop with the knife? |
| 26 | DIAG | event_object_role | short_answer | coverage | - | correct | a knife | knife | During the clip, the person chops a piece of onion. What tool do they use to chop it? |
| 27 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | wrong | A | B | During the clip, a chopping board is placed on the counter. During this action, a sound of metal or plastic co |
| 28 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | correct | A | A | During the clip, the person peels a vegetable. Just as this action starts, a cutting or chopping sound is hear |
| 29 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | correct | C | C | During the clip, the green chillies are sliced and placed into the mixer jar. During this action, a sound of m |
| 30 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | correct | B | B | During the clip, the person places the green chillies down and picks up a tool to chop them. During this actio |
| 31 | DIAG | sound_anchored_spatial_side | single_choice | same_skill_new_event | - | correct | C | C | During the clip, the person peels a vegetable. Before the peeling begins, a sound of metal and plastic collidi |
| 32 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | wrong | D | A | During the clip, a chopping board is placed on the counter. During this action, the second time a sound of met |
| 33 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | When the person takes ingredients out of the refrigerator, the first time a sound of metal and plastic collidi |
| 34 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | wrong | B | A | During the clip, a knife is placed down. During this action, a sound of metal and wood colliding is heard. Whi |
| 35 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | During the clip, the person peels an onion. During this event, a sound of metal and wood colliding is heard. W |
| 36 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | During the clip, the person peels the additional onions. Before the peeling begins, a sound of metal and wood  |
| 37 | DIAG | sound_movement_binding | - | request_verification | - | evidence_unresolved | None | None |  |
| 38 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | correct | A | A | During the clip, the sliced tomatoes are placed into the mixer. During this overall action, a sound of plastic |
| 39 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | During the clip, more tomatoes are sliced and transferred. During the slicing, cutting or chopping sounds are  |
| 40 | DIAG | sound_movement_binding | - | request_verification | - | evidence_unresolved | None | None |  |
| 41 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | During the clip, an ingredient is sliced and transferred. During the slicing, cutting or chopping sounds are h |
| 42 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | During the clip, the green chillies are sliced and placed into the mixer jar. During this action, cutting or c |
| 43 | DIAG | sound_movement_binding | short_answer | coverage | - | wrong | a knife | garlic clove | During the clip, an ingredient is added to the mixer jar. During this action, a sound of metal and plastic col |

## L3 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | cross_event_integration | single_choice | coverage | - | correct | C | C | What was the state of the onions before they were chopped? |
| 2 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | What was done to the onions before they were transferred into the bowl? |
| 3 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | What was done to the tomatoes before they were sliced? |
| 4 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | What was done to the tomatoes in the mixer jar before the green chillies were sliced into it? |
| 5 | DIAG | cross_event_integration | short_answer | coverage | - | correct | blended into a puree | They were blended into a puree | What was the state of the tomatoes when they were poured into the bowl? |
| 6 | DIAG | cross_event_integration | short_answer | coverage | - | wrong | They were weighed on the weigh | half of them were cut | Besides peeling, what was done to the onions before the remaining ones were chopped? |
| 7 | DIAG | cross_event_integration | single_choice | coverage | - | correct | C | C | When the second batch of tomatoes is sliced and placed into the mixer jar, what is already inside the jar? |
| 8 | DIAG | cross_event_integration | single_choice | coverage | - | correct | C | C | When more tomatoes are sliced and placed into the mixer jar, what happened to the knife just before this? |
| 9 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | wrong | C | A | What was the last ingredient added to the mixer jar before the blender was turned on? |
| 10 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | A | A | What was done to the green chillies before they were chopped? |
| 11 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | A | A | What was the last ingredient added to the mixer jar before the blender was turned on? |
| 12 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | A | A | What was done to the green chillies before they were chopped? |

## L4 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | C | C | What is the next step for the task the camera wearer is doing? |
| 2 | DIAG | goal_conditioned_planning | single_choice | same_skill_new_event | - | correct | B | B | What is the next step for the task the camera wearer is doing? |
| 3 | DIAG | goal_conditioned_planning | plan | coverage | - | wrong | ['Green chillies are sliced an | 1. Retrieve, prepare, and wash | What are the remaining stages, in order, for the task the camera wearer is doing? |
| 4 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | B | B | What is the next step for the task the camera wearer is doing? |
| 5 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | B | B | What is the next step for the task the camera wearer is doing? |

## Gemini 用量

| role | calls | errors | tok_in | tok_out | tok_think |
|---|---|---|---|---|---|
| examiner | 112 | 0 | 4030108 | 69234 | 445342 |
| judge | 11 | 0 | 3967 | 815 | 2169 |
| solver | 264 | 0 | 1273218 | 4328 | 0 |
