# pyramid2 run `p2_hdepicE_1023t_g4_v16_self__29`

dataset hdepic_e · videos 1 · examiner `gcp/google/gemini-3.1-pro-preview` · solver `gcp/google/gemini-4-argon` · n_per_layer 200 · seed 1023 · prompt physical-mental-draft2-hdepic-e+v16sg

**结果为 provisional**:gold = Examiner 的 proposed_reference_answer,未经人工核验;open/plan 题由 Gemini judge 判。

## 每层概览

| layer | stop | turns | scored | correct | raw acc | cluster-dedup acc | follow-up | invalid/unresolved | confirmation |
|---|---|---|---|---|---|---|---|---|---|
| L1 | STAIRCASE_COMPLETE | 22 | 22 | 14 | 0.636 | 0.611 | 0 | 0/0 | - |
| L2 | STAIRCASE_COMPLETE | 52 | 49 | 41 | 0.837 | 0.875 | 0 | 0/3 | - |
| L3 | STAIRCASE_COMPLETE | 7 | 7 | 7 | 1.0 | 1.0 | 0 | 0/0 | - |
| L4 | STAIRCASE_COMPLETE | 2 | 2 | 2 | 1.0 | 1.0 | 0 | 0/0 | - |

## 每层 × skill 诊断结论

| layer | skill | verdict | scored | correct | clusters | first-try correct | supported hypotheses | confirmation |
|---|---|---|---|---|---|---|---|---|
| L1 | spatial_near | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L1 | spatial_side | boundary<1 | 2 | 1 | 2 |  | - | - |
| L1 | object_recognition | boundary 2.5 | 12 | 9 | 10 |  | - | - |
| L1 | object_location_at_time | boundary 2.25 | 5 | 4 | 3 |  | - | - |
| L1 | object_grounding | boundary<1 | 3 | 0 | 3 |  | - | - |
| L2 | sound_action_binding | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | object_state_change | boundary>=4 | 6 | 6 | 3 |  | - | - |
| L2 | action_temporal_order | boundary 2.5 | 10 | 7 | 10 |  | - | - |
| L2 | action_recognition | boundary 3.5 | 8 | 7 | 8 |  | - | - |
| L2 | event_object_role | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | sound_anchored_spatial_near | boundary 2.0 | 1 | 1 | 1 |  | - | - |
| L2 | sound_anchored_spatial_side | boundary 1.75 | 5 | 3 | 3 |  | - | - |
| L2 | sound_movement_binding | boundary 2.75 | 7 | 5 | 3 |  | - | - |
| L3 | cross_event_integration | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L3 | hidden_state_inference | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | spatial_state_integration | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | causal_prerequisite_reasoning | boundary 2.0 | 1 | 1 | 1 |  | - | - |
| L4 | goal_conditioned_planning | boundary 2.5 | 2 | 2 | 2 |  | - | - |

## L1 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | spatial_side | single_choice | coverage | - | wrong | D | A | About 1 second into the clip, during the event where an ingredient is placed onto a digital scale, which of th |
| 2 | DIAG | spatial_side | single_choice | coverage | - | correct | C | C | About 4 seconds into the clip, when a handful of greens is pulled out of the bag, which of the following objec |
| 3 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 2 seconds into the clip, during the event where various ingredients are placed onto the kitchen counter, |
| 4 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 2 seconds into the clip, during the event where an ingredient is scooped up and dropped into a bowl, whi |
| 5 | DIAG | object_recognition | single_choice | coverage | - | correct | B | B | About 6 seconds into the clip, during the event where the camera wearer picks up an item from the plastic cove |
| 6 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 1 second into the clip, when the camera wearer chops off one end of the ingredient, which tool do they u |
| 7 | DIAG | object_recognition | short_answer | coverage | - | correct | the knife | knife | About 5 seconds into the clip, when the camera wearer places an item back onto the plastic chopping board usin |
| 8 | DIAG | object_recognition | short_answer | coverage | - | wrong | a second piece of the first to | the sliced half of the tomato | About 5 seconds into the clip, during the event where the knife slices into the first tomato, which specific o |
| 9 | DIAG | object_recognition | single_choice | coverage | - | correct | B | B | About 1.5 seconds into the clip, during the event where the seeds are removed from the second tomato, which ob |
| 10 | DIAG | object_recognition | single_choice | coverage | - | wrong | B | C | About 1 second into the clip, during the event where various ingredients are placed onto the kitchen counter,  |
| 11 | DIAG | object_recognition | single_choice | coverage | - | correct | C | C | At the start of the clip, during the event where the deseeded tomato is cut into small diced pieces, which spe |
| 12 | DIAG | object_recognition | single_choice | coverage | - | wrong | D | A | About 1 second into the clip, during the event where the second deseeded tomato is cut into small diced pieces |
| 13 | DIAG | object_recognition | single_choice | coverage | - | correct | B | B | About 4.5 seconds into the clip, during the event where the knife rapidly cuts the onion halves into fine piec |
| 14 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 8 seconds into the clip, during the event where various ingredients are placed onto the kitchen counter, |
| 15 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 5 seconds into the clip, during the event where various ingredients are placed onto the kitchen counter, |
| 16 | DIAG | object_location_at_time | single_choice | coverage | - | wrong | C | A | At the end of the clip, during the event where a crinkling sound is made by the plastic bag being manipulated, |
| 17 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 1 second into the clip, during the event where an ingredient is scooped up and dropped into a bowl, wher |
| 18 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | At the end of the clip, during the event where a crinkling sound is made by the plastic bag being manipulated, |
| 19 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | At the start of the clip, during the event where the plastic bag containing lettuce is torn open, where does t |
| 20 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.57, 0.73, 0.73, 0.81] | 53.8, 64.4, 69.4, 75.0 | About 0.3 seconds into the clip, when a handful of lettuce is pulled out of the bag, what is the bounding box  |
| 21 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.61, 0.52, 0.7, 0.72] | 51.1, 56.8, 66.3, 69.7 | At the start of the clip, when a handful of lettuce is pulled out of the bag, what is the bounding box of the  |
| 22 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.569, 0.577, 0.639, 0.681] | 54.7, 56.1, 67.7, 72.6 | At the start of the clip, during the event where the outer skin is peeled off the onion, what is the bounding  |

## L2 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | While various ingredients are being placed onto the kitchen counter, a sharp snapping or cutting sound is hear |
| 2 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, a crinkling sound is heard. Which action produces this sound? |
| 3 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, sharp chopping sounds are heard. Which of the following actions pr |
| 4 | DIAG | sound_action_binding | single_choice | coverage | - | correct | B | B | During the task the camera wearer is doing, rapid chopping sounds are heard. Which of the following actions pr |
| 5 | DIAG | sound_action_binding | short_answer | coverage | - | correct | Lifting a bowl from a stack of | picking up the bowl | While the chopped onion pieces are scooped up and dropped into a bowl, a ceramic collision sound is heard. Wha |
| 6 | DIAG | sound_action_binding | short_answer | coverage | - | correct | Scraping the knife against the | Scraping the chopping board wi | During the event where a chopping board is set down on the workspace, a continuous scraping sound is heard. Wh |
| 7 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the pack of fresh romaine lettuce is taken out of the refrigerator, where is it placed? |
| 8 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the pair of scissors is taken out of the drawer and used to cut the plastic cover, where is it placed aft |
| 9 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the small bowl is picked up to receive the chopped onion pieces, where is it taken from? |
| 10 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the onion is picked up from the bag of onions, where is it placed? |
| 11 | DIAG | object_state_change | short_answer | coverage | - | correct | On the wooden cutting board | On the wooden chopping board | When the pack of fresh romaine lettuce is taken out of the refrigerator, where is it placed? |
| 12 | DIAG | object_state_change | short_answer | same_event_new_format | - | correct | On the white cutting board | On the plastic chopping board | During the task the camera wearer is doing, a pair of scissors is taken out of a drawer and used to cut the pl |
| 13 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the event where various ingredients are placed onto the kitchen counter, what action happens immediatel |
| 14 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, what action happens immediately after the pair of scissors is put  |
| 15 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, what action happens immediately after the onion is cut into two ha |
| 16 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, what action happens immediately after the chopped pieces of onion  |
| 17 | DIAG | action_temporal_order | short_answer | coverage | - | correct | A white bowl is taken down and | Picking up a small bowl | During the event where the chopped onion pieces are scooped up and dropped into a bowl, what action happens im |
| 18 | DIAG | action_temporal_order | short_answer | coverage | - | wrong | A tomato is placed on a plate  | The knife is placed back onto  | During the event where a chopping board is set down on the workspace, what action happens immediately after th |
| 19 | DIAG | action_temporal_order | single_choice | coverage | - | wrong | B | A | During the task the camera wearer is doing, what action happens immediately after the other half of the tomato |
| 20 | DIAG | action_temporal_order | single_choice | coverage | - | wrong | D | B | During the task the camera wearer is doing, what action happens immediately after the first part of the sliced |
| 21 | DIAG | action_temporal_order | single_choice | coverage | - | correct | B | B | During the task the camera wearer is doing, what action happens immediately after the inner part of the tomato |
| 22 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the event where the second deseeded tomato is cut into small diced pieces, what action happens immediat |
| 23 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the event where various ingredients are placed onto the kitchen counter, which of the following actions |
| 24 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the event where the plastic cover is pulled apart to make a bigger opening, what action is performed wi |
| 25 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the event where the first half of the chopped onion is picked up, which of the following actions is per |
| 26 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the event where the piece of onion is rotated to expose its unchopped end, which of the following actio |
| 27 | DIAG | action_recognition | short_answer | coverage | - | correct | Transferring the chopped onion | It clumps together the chopped | During the event where the small bowl is placed on the plastic chopping board using the left hand, what action |
| 28 | DIAG | action_recognition | short_answer | coverage | - | wrong | It is scraped off the chopping | Moving it from the plate to th | During the event where the knife is used to scrape the plastic chopping board, what action is performed with t |
| 29 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the event where the seeds are removed from the sliced half of the tomato to leave only the outer shell, |
| 30 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the event where one of the remaining parts of the sliced tomato is picked up, which of the following ac |
| 31 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | During the event where various ingredients are placed onto the kitchen counter, what object is the pack of fre |
| 32 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | During the event where the piece of romaine lettuce is put down, what object is it placed on? |
| 33 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | During the event where the outer skin is peeled off the onion, what object is the peel placed on? |
| 34 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | During the event where the chopped pieces of onion are rotated to make even finer chops, what tool is used? |
| 35 | DIAG | event_object_role | short_answer | coverage | - | correct | A small bowl | A bowl | During the event where the chopped onion pieces are scooped up, what object are they dropped into? |
| 36 | DIAG | event_object_role | short_answer | coverage | - | correct | A white bowl on a digital kitc | A weighing scale | During the event where a whole tomato is put down, what object is it placed onto? |
| 37 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | correct | B | B | During the event where various ingredients are placed onto the kitchen counter, at the moment an opening or cl |
| 38 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | correct | B | B | During the event where various ingredients are placed onto the kitchen counter, at the moment a cutting or cho |
| 39 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | correct | C | C | During the event where a crinkling sound is made by the plastic bag being manipulated, from the camera wearer' |
| 40 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | wrong | D | A | During the event where a chopping board is set down on the workspace, at the moment a ceramic collision sound  |
| 41 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | wrong | C | B | During the event where a whole tomato is placed onto a digital scale, at the moment a metal or wood collision  |
| 42 | DIAG | sound_anchored_spatial_side | - | request_verification | - | evidence_unresolved | None | None |  |
| 43 | DIAG | sound_anchored_spatial_side | single_choice | same_skill_new_event | - | correct | B | B | During the event where a handful of lettuce is pulled out of the bag, at the moment the second metal or plasti |
| 44 | DIAG | sound_anchored_spatial_side | - | request_verification | - | evidence_unresolved | None | None |  |
| 45 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | B | B | During the event where various ingredients are placed onto the kitchen counter, a light collision sound is hea |
| 46 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | During the event where a handful of lettuce is pulled out of the bag, the second metal or plastic collision so |
| 47 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | During the event where the chopped onion pieces are scooped up and dropped into a bowl, a ceramic collision so |
| 48 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | During the event where various ingredients are placed onto the kitchen counter, the first metal or plastic col |
| 49 | DIAG | sound_movement_binding | short_answer | coverage | - | correct | The camera wearer places the o | Moving the onion to the counte | During the event where various ingredients are placed onto the kitchen counter, a light collision sound is hea |
| 50 | DIAG | sound_movement_binding | short_answer | coverage | - | wrong | Retrieving scissors from the c | Cutting the plastic cover with | During the event where a crinkling sound is made by the plastic bag being manipulated, the first metal or plas |
| 51 | DIAG | sound_movement_binding | single_choice | same_event_new_format | - | wrong | D | A | During the event where a crinkling sound is made by the plastic bag being manipulated, the first metal or plas |
| 52 | DIAG | sound_movement_binding | - | request_verification | - | evidence_unresolved | None | None |  |

## L3 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | What state was the onion in immediately before it was finely chopped? |
| 2 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | C | C | What is the state of the ingredient being transferred into the bowl? |
| 3 | DIAG | cross_event_integration | single_choice | coverage | - | correct | C | C | When the tomato is being chopped, what part of it is missing? |
| 4 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | C | C | What part of the second tomato is missing when it is being chopped? |
| 5 | DIAG | cross_event_integration | short_answer | coverage | - | correct | Its ends are cut off, it is ha | It was peeled and cut in half. | What was done to the onion before it is finely chopped? |
| 6 | DIAG | cross_event_integration | short_answer | coverage | - | correct | It was weighed on the kitchen  | It was weighed on a scale and  | What was done to the tomato before its seeds are scraped out? |
| 7 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | A | A | In the clip, what is done to the tomato before it is cut into? |

## L4 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | C | C | What is the next step the camera wearer will take for the task they are doing? |
| 2 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | C | C | What is the next step the camera wearer will take for the task they are doing? |

## Gemini 用量

| role | calls | errors | tok_in | tok_out | tok_think |
|---|---|---|---|---|---|
| examiner | 95 | 1 | 2629983 | 57308 | 324256 |
| judge | 33 | 0 | 9136 | 1724 | 5690 |
| scope | 1 | 0 | 1709 | 3424 | 2911 |
| solver | 240 | 0 | 1063410 | 4096 | 0 |
