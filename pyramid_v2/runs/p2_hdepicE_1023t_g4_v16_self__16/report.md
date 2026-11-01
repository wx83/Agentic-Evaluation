# pyramid2 run `p2_hdepicE_1023t_g4_v16_self__16`

dataset hdepic_e · videos 1 · examiner `gcp/google/gemini-3.1-pro-preview` · solver `gcp/google/gemini-4-argon` · n_per_layer 200 · seed 1023 · prompt physical-mental-draft2-hdepic-e+v16sg

**结果为 provisional**:gold = Examiner 的 proposed_reference_answer,未经人工核验;open/plan 题由 Gemini judge 判。

## 每层概览

| layer | stop | turns | scored | correct | raw acc | cluster-dedup acc | follow-up | invalid/unresolved | confirmation |
|---|---|---|---|---|---|---|---|---|---|
| L1 | STAIRCASE_COMPLETE | 18 | 18 | 13 | 0.722 | 0.706 | 0 | 0/0 | - |
| L2 | STAIRCASE_COMPLETE | 49 | 48 | 43 | 0.896 | 0.932 | 0 | 0/1 | - |
| L3 | STAIRCASE_COMPLETE | 12 | 12 | 12 | 1.0 | 1.0 | 0 | 0/0 | - |
| L4 | STAIRCASE_COMPLETE | 1 | 1 | 1 | 1.0 | 1.0 | 0 | 0/0 | - |

## 每层 × skill 诊断结论

| layer | skill | verdict | scored | correct | clusters | first-try correct | supported hypotheses | confirmation |
|---|---|---|---|---|---|---|---|---|
| L1 | spatial_near | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L1 | spatial_side | boundary 3.5 | 3 | 3 | 2 |  | - | - |
| L1 | object_recognition | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L1 | object_location_at_time | boundary 2 | 6 | 4 | 6 |  | - | - |
| L1 | object_grounding | boundary<1 | 3 | 0 | 3 |  | - | - |
| L2 | sound_action_binding | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | object_state_change | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | action_temporal_order | boundary 3.5 | 7 | 6 | 7 |  | - | - |
| L2 | action_recognition | boundary 3.5 | 8 | 7 | 8 |  | - | - |
| L2 | event_object_role | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | sound_anchored_spatial_near | boundary 2.0 | 1 | 1 | 1 |  | - | - |
| L2 | sound_anchored_spatial_side | boundary 2 | 8 | 5 | 4 |  | - | - |
| L2 | sound_movement_binding | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L3 | cross_event_integration | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L3 | hidden_state_inference | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | spatial_state_integration | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | causal_prerequisite_reasoning | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L4 | goal_conditioned_planning | boundary 2.0 | 1 | 1 | 1 |  | - | - |

## L1 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | spatial_side | single_choice | coverage | - | correct | C | C | About 1 second into the clip, as the camera wearer handles a chicken piece, which of the following objects is  |
| 2 | DIAG | spatial_side | single_choice | coverage | - | correct | C | C | About 1.5 seconds into the clip, as the bowl is placed on the counter, from the camera wearer's own viewpoint  |
| 3 | DIAG | spatial_side | single_choice | coverage | - | correct | C | C | About 3 seconds into the clip, as the packaging of chicken is handled, which of the following objects is farth |
| 4 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 5.5 seconds into the clip, as the items are washed under running water, which object is being handled? |
| 5 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | At the start of the clip, as vinegar is poured from its bottle into the bowl over the chicken, which of the fo |
| 6 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 4.5 seconds into the clip, as the chicken container is opened, which object is the camera wearer holding |
| 7 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 1 second into the clip, during the process of placing the remaining items into the bowl, as the camera w |
| 8 | DIAG | object_recognition | short_answer | coverage | - | correct | the fridge | fridge door | About 1.5 seconds into the clip, soy sauce is poured into the bowl. At the very start of the clip, just before |
| 9 | DIAG | object_recognition | short_answer | coverage | - | correct | a slice of lemon | lemon | At the start of the clip, as an item is moved on the chopping board to position it closer to the countertop, w |
| 10 | DIAG | object_location_at_time | single_choice | coverage | - | wrong | B | A | About 8 seconds into the clip, as the chicken pieces are washed under running water, to which surface or fixtu |
| 11 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 1.5 seconds into the clip, as the bowl is placed down, to which surface or fixture is it moved? |
| 12 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 6.5 seconds into the clip, as the remaining chicken pieces are washed under the tap, to which surface or |
| 13 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 1.5 seconds into the clip, as soy sauce is poured into the bowl, to which surface or fixture is the bott |
| 14 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 1 second into the clip, as a head of garlic is broken apart into individual cloves, to which surface or  |
| 15 | DIAG | object_location_at_time | single_choice | coverage | - | wrong | B | A | About 4 seconds into the clip, a lemon half is squeezed over the bowl. At the start of the clip, as the lemon  |
| 16 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.458, 0.675, 0.673, 0.868] | 56.4, 71.1, 70.8, 84.3 | Please provide the bounding box for the chicken piece in the first frame of the clip. |
| 17 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.059, 0.653, 0.074, 0.868] | 61.2, 58.5, 78.5, 78.8 | Please provide the bounding box for the bowl in the first frame of the clip. |
| 18 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.72, 0.53, 0.98, 0.76] | 59.7, 57.1, 88.0, 80.7 | Please provide the bounding box for the bowl in the first frame of the clip. |

## L2 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | Which sound is heard when the camera wearer picks up the bowl from the dishwasher? |
| 2 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | Which sound is heard when the camera wearer struggles to pull the frozen chicken pieces from the container? |
| 3 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | Which sound is produced by the action of placing the first separated chicken piece into the bowl? |
| 4 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | Which sound is heard when the camera wearer picks up the bottle of vinegar from the shelf? |
| 5 | DIAG | sound_action_binding | short_answer | coverage | - | correct | pouring soy sauce into the bow | pouring soy sauce into the bow | A liquid pouring sound is heard in the clip. What action involving the soy sauce and the bowl produces this so |
| 6 | DIAG | sound_action_binding | short_answer | coverage | - | correct | closing the drawer | opening a drawer | In the clip, a lemon half is squeezed over the bowl. Just before this, a sliding sound is heard. What action p |
| 7 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the bowl is placed on the counter, where was it taken from? |
| 8 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the washed chicken pieces are moved from the sink, where are they placed? |
| 9 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the washed chicken piece is moved to the counter, where is it taken from? |
| 10 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the bottle of soy sauce is placed on the counter, where was it taken from? |
| 11 | DIAG | object_state_change | short_answer | coverage | - | correct | a drawer | drawer | When the camera wearer retrieves the lemon squeezer, where is it taken from? |
| 12 | DIAG | object_state_change | short_answer | coverage | - | correct | over the bowl of chicken | on top of the bowl | When the camera wearer picks up the lemon juicer from the chopping board, where is it moved to? |
| 13 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | What does the camera wearer do immediately after picking up the knife from the countertop? |
| 14 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | What does the camera wearer do immediately after separating the two chicken pieces under the tap? |
| 15 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | What does the camera wearer do immediately after breaking off a chicken piece and putting it into the bowl? |
| 16 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | What does the camera wearer do immediately after pouring vinegar into the lid for the first time? |
| 17 | DIAG | action_temporal_order | short_answer | coverage | - | wrong | pours more soy sauce into the  | looks into the bottle | What does the camera wearer do immediately after pouring soy sauce into the bowl for the first time? |
| 18 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | What does the camera wearer do immediately after picking up the first lemon half from the chopping board? |
| 19 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | What does the camera wearer do immediately after cutting the lemon into two halves? |
| 20 | DIAG | action_recognition | single_choice | coverage | - | correct | B | B | How does the camera wearer open the chicken container? |
| 21 | DIAG | action_recognition | single_choice | coverage | - | correct | B | B | How does the camera wearer separate the two connected chicken pieces while washing them under the tap? |
| 22 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the clip, the camera wearer struggles to separate the frozen chicken pieces under the tap. How do they  |
| 23 | DIAG | action_recognition | single_choice | coverage | - | correct | B | B | During the clip, the camera wearer adds vinegar to the bowl containing the chicken. How do they do this? |
| 24 | DIAG | action_recognition | short_answer | coverage | - | correct | shaking it repeatedly | shaking the bottle | During the clip, the camera wearer pours soy sauce into the bowl. What specific motion do they make with the b |
| 25 | DIAG | action_recognition | short_answer | coverage | - | wrong | picks it out with their right  | sliding it up the side of the  | During the clip, a lemon seed falls into the bowl. What specific action does the camera wearer take to remove  |
| 26 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the clip, the camera wearer cuts a lemon into two halves. How do they separate the two halves after cut |
| 27 | DIAG | action_recognition | single_choice | coverage | - | correct | B | B | During the clip, the camera wearer puts rosemary into the bowl. How do they transfer it from the package? |
| 28 | DIAG | event_object_role | single_choice | coverage | - | correct | B | B | During the clip, the camera wearer opens the chicken container. What tool do they use to pierce and tear the p |
| 29 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | During the clip, the camera wearer places the washed chicken pieces down. What container do they place them in |
| 30 | DIAG | event_object_role | single_choice | coverage | - | correct | B | B | During the clip, the camera wearer forcefully pulls a chicken piece to separate it. What object does their han |
| 31 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | During the clip, the camera wearer pours vinegar from the bottle. What object do they pour the vinegar into be |
| 32 | DIAG | event_object_role | short_answer | coverage | - | correct | the bowl | a bowl | During the clip, the camera wearer pours soy sauce. What container do they pour it into? |
| 33 | DIAG | event_object_role | short_answer | coverage | - | correct | a lemon squeezer | a lemon squeezer | During the clip, the camera wearer squeezes a lemon half. What tool do they use to squeeze it? |
| 34 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | correct | A | A | During the clip, a clattering sound of metal and plastic is heard. At that moment, which of the following obje |
| 35 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | correct | B | B | During the clip, the bowl is placed on the counter, producing a ceramic collision sound. At the moment of that |
| 36 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | correct | B | B | During the clip, a collision sound is heard when the camera wearer attempts to pick up the frozen chicken piec |
| 37 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | wrong | D | C | During the clip, a water sound is heard when the camera wearer closes the second handle of the tap. At the mom |
| 38 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | correct | C | C | During the clip, a metal and wood collision sound is heard. At the moment of that sound, from the camera weare |
| 39 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | wrong | B | A | During the clip, a water sound is heard when the camera wearer closes the second handle of the tap. At the mom |
| 40 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | wrong | A | B | During the clip, a ceramic collision sound is heard when the bowl is placed on the counter. At the moment of t |
| 41 | DIAG | sound_anchored_spatial_side | single_choice | same_skill_cleaner_event | - | correct | B | B | During the clip, the first metal and wood collision sound is heard. At the moment of that sound, from the came |
| 42 | DIAG | sound_anchored_spatial_side | - | request_verification | - | evidence_unresolved | None | None |  |
| 43 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | correct | D | D | During the clip, a metal and wood collision sound is heard. At the moment of that sound, from the camera weare |
| 44 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | During the clip, a clattering sound is heard right at the beginning. Which movement produces this sound? |
| 45 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | During the clip, clattering sounds of metal and wood are heard. Which movement produces these sounds? |
| 46 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | During the clip, a sound of metal and plastic colliding is heard. Which movement produces this sound? |
| 47 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | During the clip, a liquid pouring sound is heard. Which movement produces this sound? |
| 48 | DIAG | sound_movement_binding | short_answer | coverage | - | correct | closing the drawer | closing the drawer | During the clip, a sliding sound is heard shortly after the camera wearer picks up the lemon squeezer. What mo |
| 49 | DIAG | sound_movement_binding | short_answer | coverage | - | correct | Cutting the lemon with the kni | moving the knife in a sawing m | During the clip, another lemon is cut in half with a knife on a cutting board. A cutting sound is heard. What  |

## L3 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | cross_event_integration | single_choice | coverage | - | correct | B | B | For the task the camera wearer is doing, what is already in the bowl when the remaining chicken is added? |
| 2 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | For the task the camera wearer is doing, what liquid is already in the bowl when the soy sauce is poured? |
| 3 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | For the task the camera wearer is doing, how did the state of the garlic change before it was chopped? |
| 4 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | For the task the camera wearer is doing, what container were the chicken pieces taken from before they were pl |
| 5 | DIAG | cross_event_integration | short_answer | coverage | - | correct | It was opened using a knife | It was cut open with a knife. | For the task the camera wearer is doing, what was done to the chicken's packaging before the chicken pieces we |
| 6 | DIAG | cross_event_integration | short_answer | same_skill_new_event | - | correct | The first two connected chicke | The first batch of chicken pie | For the task the camera wearer is doing, what was done to the chicken pieces before the remaining ones were wa |
| 7 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | A | A | For the task the camera wearer is doing, which earlier action provided the container that the washed chicken p |
| 8 | DIAG | causal_prerequisite_reasoning | single_choice | same_skill_new_event | - | correct | B | B | For the task the camera wearer is doing, what had to be done to the garlic before the individual cloves could  |
| 9 | DIAG | causal_prerequisite_reasoning | single_choice | same_skill_new_event | - | correct | A | A | For the task the camera wearer is doing, which earlier action provided the container that the washed chicken p |
| 10 | DIAG | causal_prerequisite_reasoning | single_choice | same_skill_new_event | - | correct | A | A | For the task the camera wearer is doing, what had to be done to the garlic before the individual cloves could  |
| 11 | DIAG | causal_prerequisite_reasoning | short_answer | coverage | - | correct | taking the white bowl out of t | The bowl was placed on the cou | For the task the camera wearer is doing, what earlier action provided the container that the washed chicken pi |
| 12 | DIAG | causal_prerequisite_reasoning | short_answer | same_event_new_format | - | correct | breaking the head of garlic ap | The head of garlic was broken  | For the task the camera wearer is doing, what had to be done to the garlic before the individual cloves could  |

## L4 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | A | A | Based on the task the camera wearer is doing, what is the next step? |

## Gemini 用量

| role | calls | errors | tok_in | tok_out | tok_think |
|---|---|---|---|---|---|
| examiner | 88 | 0 | 2481587 | 53957 | 318373 |
| judge | 21 | 0 | 6035 | 1122 | 3651 |
| scope | 1 | 0 | 1746 | 3681 | 3982 |
| solver | 237 | 0 | 1302462 | 3998 | 0 |
