# pyramid2 run `p2_hdepicE_1023t_g4_v16_goldlive__29`

dataset hdepic_e · videos 1 · examiner `gcp/google/gemini-3.1-pro-preview` · solver `gcp/google/gemini-4-argon` · n_per_layer 200 · seed 1023 · prompt physical-mental-draft2-hdepic-e+v16sg

**结果为 provisional**:gold = Examiner 的 proposed_reference_answer,未经人工核验;open/plan 题由 Gemini judge 判。

## 每层概览

| layer | stop | turns | scored | correct | raw acc | cluster-dedup acc | follow-up | invalid/unresolved | confirmation |
|---|---|---|---|---|---|---|---|---|---|
| L1 | STAIRCASE_COMPLETE | 17 | 17 | 11 | 0.647 | 0.688 | 0 | 0/0 | - |
| L2 | STAIRCASE_COMPLETE | 52 | 51 | 44 | 0.863 | 0.872 | 0 | 1/0 | - |
| L3 | STAIRCASE_COMPLETE | 7 | 7 | 7 | 1.0 | 1.0 | 0 | 0/0 | - |
| L4 | STAIRCASE_COMPLETE | 2 | 2 | 2 | 1.0 | 1.0 | 0 | 0/0 | - |

## 每层 × skill 诊断结论

| layer | skill | verdict | scored | correct | clusters | first-try correct | supported hypotheses | confirmation |
|---|---|---|---|---|---|---|---|---|
| L1 | spatial_near | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L1 | spatial_side | boundary<1 | 2 | 1 | 2 |  | - | - |
| L1 | object_recognition | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L1 | object_location_at_time | boundary<1 | 4 | 2 | 3 |  | - | - |
| L1 | object_grounding | boundary<1 | 5 | 2 | 5 |  | - | - |
| L2 | sound_action_binding | boundary 2 | 7 | 5 | 7 |  | - | - |
| L2 | object_state_change | boundary>=4 | 6 | 6 | 3 |  | - | - |
| L2 | action_temporal_order | boundary 2.5 | 12 | 9 | 10 |  | - | - |
| L2 | action_recognition | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | event_object_role | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | sound_anchored_spatial_near | boundary 2.0 | 1 | 1 | 1 |  | - | - |
| L2 | sound_anchored_spatial_side | boundary 2 | 7 | 5 | 3 |  | - | - |
| L2 | sound_movement_binding | boundary>=4 | 6 | 6 | 3 |  | - | - |
| L3 | cross_event_integration | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L3 | hidden_state_inference | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | spatial_state_integration | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | causal_prerequisite_reasoning | boundary 2.0 | 1 | 1 | 1 |  | - | - |
| L4 | goal_conditioned_planning | boundary 2.5 | 2 | 2 | 2 |  | - | - |

## L1 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | spatial_side | single_choice | coverage | - | wrong | C | B | About 1 second into the clip, when the bowl is moved, from the camera wearer's own viewpoint at that moment (e |
| 2 | DIAG | spatial_side | single_choice | coverage | - | correct | A | A | About 4 seconds into the clip, just before a handful of leaves is pulled out of the bag, from the camera weare |
| 3 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 2 seconds into the clip, as various ingredients are placed onto the kitchen counter, what object does th |
| 4 | DIAG | object_recognition | single_choice | coverage | - | correct | B | B | About 5 seconds into the clip, when the ingredients are scooped up and dropped into a bowl, what does the came |
| 5 | DIAG | object_recognition | single_choice | coverage | - | correct | C | C | About 6 seconds into the clip, when the camera wearer picks something up from the plastic cover, what object i |
| 6 | DIAG | object_recognition | single_choice | coverage | - | correct | B | B | About 4 seconds into the clip, when the camera wearer rotates an object to expose its other end, what object i |
| 7 | DIAG | object_recognition | short_answer | coverage | - | correct | Knife | knife | About 5 seconds into the clip, when the camera wearer places something back onto the plastic chopping board us |
| 8 | DIAG | object_recognition | short_answer | coverage | - | correct | the knife | Knife | About 5 seconds into the clip, when the camera wearer picks something back up to slice into the tomato, what o |
| 9 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 5 seconds into the clip, as various ingredients are placed, where is the pack of fresh romaine lettuce p |
| 10 | DIAG | object_location_at_time | single_choice | coverage | - | wrong | B | A | About 10 seconds into the clip, after a crinkling sound is made by the plastic bag being manipulated, where ar |
| 11 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 2 seconds into the clip, when the chopped onion pieces are scooped up and dropped into a bowl, where is  |
| 12 | DIAG | object_location_at_time | single_choice | same_event_new_format | - | wrong | B | A | About 10 seconds into the clip, after a crinkling sound is made by the plastic bag being manipulated, where ar |
| 13 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.604, 0.622, 0.65, 0.682] | 53.8, 64.4, 69.4, 75.0 | At the start of the clip, just before a handful of lettuce is pulled out of the bag, please provide the boundi |
| 14 | DIAG | object_grounding | bbox | coverage | - | correct | [0.604, 0.52, 0.71, 0.692] | 51.1, 56.8, 66.3, 69.7 | At the start of the clip, when a piece of lettuce is picked up, please provide the bounding box of the lettuce |
| 15 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.56, 0.56, 0.65, 0.67] | 54.7, 56.1, 67.7, 72.6 | At the start of the clip, when the outer skin is peeled off the onion, please provide the bounding box of the  |
| 16 | DIAG | object_grounding | bbox | coverage | - | correct | [0.396, 0.61, 0.545, 0.766] | 40.0, 60.7, 55.4, 76.8 | At the start of the clip, when the chopped onion pieces are scooped up and dropped into a bowl, please provide |
| 17 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.519, 0.533, 0.589, 0.592] | 46.5, 55.0, 51.3, 59.0 | At the start of the clip, as various ingredients are placed onto the kitchen counter, please provide the bound |

## L2 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | When the various ingredients are being retrieved and placed onto the kitchen counter, a closing sound is heard |
| 2 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, which of the following actions produces a sound of metal colliding |
| 3 | DIAG | sound_action_binding | single_choice | coverage | - | wrong | D | A | During the task the camera wearer is doing, which of the following actions produces a sound of metal or cerami |
| 4 | DIAG | sound_action_binding | single_choice | coverage | - | correct | C | C | During the task the camera wearer is doing, which of the following actions produces a series of rapid chopping |
| 5 | DIAG | sound_action_binding | single_choice | coverage | - | wrong | B | A | When the chopped onion pieces are scooped up and dropped into a bowl, which of the following sounds is heard? |
| 6 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, which of the following actions produces a scraping or mixing sound |
| 7 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | In the clip, which of the following actions produces a cutting or chopping sound? |
| 8 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when the pack of fresh romaine lettuce is retrieved from the refri |
| 9 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when the pair of scissors is retrieved from the drawer, where is i |
| 10 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when the small bowl is retrieved from the cupboard, where is it pl |
| 11 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when the onion is retrieved from the bag of onions, where is it pl |
| 12 | DIAG | object_state_change | short_answer | same_event_new_format | - | correct | On the wooden chopping board | on the chopping board | During the task the camera wearer is doing, when the pack of fresh romaine lettuce is retrieved from the refri |
| 13 | DIAG | object_state_change | short_answer | same_event_new_format | - | item_invalid | None | On the plastic chopping board | During the task the camera wearer is doing, a crinkling sound is made by the plastic bag being manipulated. Ar |
| 14 | DIAG | object_state_change | short_answer | same_event_new_format | - | correct | On the counter | On the plastic chopping board | During the task the camera wearer is doing, when the small bowl is retrieved from the cupboard, where is it pl |
| 15 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | When the various ingredients are being retrieved and placed onto the kitchen counter, which of the following a |
| 16 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | C | C | In the clip, which of the following actions happens first? |
| 17 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | In the clip, which of the following actions happens first? |
| 18 | DIAG | action_temporal_order | single_choice | coverage | - | correct | B | B | In the clip, which of the following actions happens first? |
| 19 | DIAG | action_temporal_order | short_answer | coverage | - | correct | Sets the bowl aside on the woo | Place the bowl on the chopping | In the clip, what action does the camera wearer do immediately after dropping the last few bits of onion piece |
| 20 | DIAG | action_temporal_order | short_answer | coverage | - | wrong | Moves the tomato back to the c | Moves the onion to the choppin | During the task the camera wearer is doing, what action does the camera wearer do immediately after placing th |
| 21 | DIAG | action_temporal_order | single_choice | coverage | - | correct | C | C | In the clip, which of the following actions happens first? |
| 22 | DIAG | action_temporal_order | single_choice | coverage | - | wrong | A | C | When the deseeded tomato is cut into small diced pieces, which of the following actions happens first? |
| 23 | DIAG | action_temporal_order | single_choice | coverage | - | correct | C | C | When the seeds are first removed from the second tomato in the clip, which of the following actions does the c |
| 24 | DIAG | action_temporal_order | single_choice | coverage | - | wrong | A | C | When the second deseeded tomato is cut into small diced pieces, which of the following actions happens first? |
| 25 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | When the various ingredients are being retrieved and placed onto the kitchen counter, which of the following a |
| 26 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | When the camera wearer pulls apart the plastic cover to make a bigger opening, which of the following actions  |
| 27 | DIAG | action_recognition | single_choice | coverage | - | correct | C | C | In the clip, what action does the camera wearer perform with the pack of fresh romaine lettuce after grabbing  |
| 28 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | In the clip, what action does the camera wearer perform with the piece of romaine lettuce after taking it out  |
| 29 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | In the clip, what action does the camera wearer perform with the two halves of the onion after cutting the oni |
| 30 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | B | B | In the clip, what action does the camera wearer perform with the piece of onion after rotating it to expose th |
| 31 | DIAG | action_recognition | short_answer | coverage | - | correct | Puts them into a white bowl | Puts them into a bowl | In the clip, what action does the camera wearer perform with the chopped onion pieces after clumping them toge |
| 32 | DIAG | action_recognition | short_answer | coverage | - | correct | places it back onto the choppi | Places the knife onto the chop | In the clip, what action does the camera wearer perform with the knife immediately after using it to scrape th |
| 33 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | When various ingredients are placed onto the kitchen counter, which of the following items is among those plac |
| 34 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | In the clip, when the camera wearer puts down the piece of romaine lettuce after taking it out of the plastic  |
| 35 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | In the clip, when the outer layer is peeled away from the onion halves, where are the peels placed? |
| 36 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | In the clip, when the knife is used to rapidly cut the ingredient into fine pieces, which of the following ing |
| 37 | DIAG | event_object_role | short_answer | coverage | - | correct | A white bowl | A bowl | In the clip, when the chopped onion pieces are scooped up, what are they dropped into? |
| 38 | DIAG | event_object_role | short_answer | coverage | - | correct | A tomato | A tomato | In the clip, what ingredient does the camera wearer place on the weighing scale? |
| 39 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | correct | B | B | When the various ingredients are being retrieved and placed onto the kitchen counter, the first time a door op |
| 40 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | correct | C | C | When the various ingredients are being retrieved and placed onto the kitchen counter, a cutting or chopping so |
| 41 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | correct | A | A | In the clip, when a crinkling sound is made by the plastic bag being manipulated, from the camera wearer's own |
| 42 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when a chopping board is set down on the workspace, a sound of cer |
| 43 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | wrong | B | A | When the various ingredients are being retrieved and placed onto the kitchen counter, a cutting or chopping so |
| 44 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | wrong | D | A | During the task the camera wearer is doing, around the time a whole tomato is placed onto a digital scale, a s |
| 45 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | correct | A | A | When various ingredients are placed onto the kitchen counter, a cutting or chopping sound is heard. At that mo |
| 46 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | correct | B | B | In the clip, when a crinkling sound is made by the plastic bag being manipulated, from the camera wearer's own |
| 47 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | When the various ingredients are being retrieved and placed onto the kitchen counter, which of the following o |
| 48 | DIAG | sound_movement_binding | single_choice | same_skill_cleaner_event | - | correct | A | A | In the clip, when the first sound of metal colliding with plastic is heard, which of the following objects is  |
| 49 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | B | B | In the clip, when the chopped onion pieces are scooped up and dropped into a bowl, a sound of ceramic collidin |
| 50 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | When the various ingredients are being retrieved and placed onto the kitchen counter, the first time a sound o |
| 51 | DIAG | sound_movement_binding | short_answer | same_event_new_format | - | correct | A bunch of fresh tomatoes | The bunch of tomatoes | When the various ingredients are being retrieved and placed onto the kitchen counter, which object is being mo |
| 52 | DIAG | sound_movement_binding | short_answer | same_event_new_format | - | correct | A pair of scissors | A pair of scissors and a pack  | In the clip, when the first sound of metal colliding with plastic is heard, what object is being moved? |

## L3 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | cross_event_integration | single_choice | coverage | - | correct | B | B | What state was the onion in immediately before it was finely chopped? |
| 2 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | What is the state of the ingredient being transferred into the bowl? |
| 3 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | What was done to the tomato before it is finely chopped? |
| 4 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | What part of the second tomato is missing when it is being chopped? |
| 5 | DIAG | cross_event_integration | short_answer | same_skill_new_event | - | correct | It is weighed on the scale, th | It was peeled and halved. | What was done to the onion before it is finely chopped? |
| 6 | DIAG | cross_event_integration | short_answer | same_skill_new_event | - | correct | It was weighed on the scale an | It was weighed and cut in half | What was done to the tomato before its seeds are scraped out? |
| 7 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | B | B | Which tomato is being cut into? |

## L4 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | C | C | What is the next step the camera wearer will take for the task they are doing? |
| 2 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | B | B | What is the next step the camera wearer will take for the task they are doing? |

## Gemini 用量

| role | calls | errors | tok_in | tok_out | tok_think |
|---|---|---|---|---|---|
| examiner | 87 | 0 | 2445204 | 56686 | 334279 |
| judge | 15 | 0 | 4329 | 810 | 2388 |
| solver | 231 | 0 | 1031790 | 3932 | 0 |
