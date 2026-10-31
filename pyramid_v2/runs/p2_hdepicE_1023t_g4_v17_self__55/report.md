# pyramid2 run `p2_hdepicE_1023t_g4_v17_self__55`

dataset hdepic_e · videos 1 · examiner `gcp/google/gemini-3.1-pro-preview` · solver `gcp/google/gemini-4-argon` · n_per_layer 200 · seed 1023 · prompt physical-mental-draft2-hdepic-e+v16sg

**结果为 provisional**:gold = Examiner 的 proposed_reference_answer,未经人工核验;open/plan 题由 Gemini judge 判。

## 每层概览

| layer | stop | turns | scored | correct | raw acc | cluster-dedup acc | follow-up | invalid/unresolved | confirmation |
|---|---|---|---|---|---|---|---|---|---|
| L1 | EVENT_LOOP_COMPLETE | 25 | 25 | 16 | 0.64 | 0.64 | 0 | 0/0 | - |
| L2 | EVENT_LOOP_COMPLETE | 58 | 57 | 43 | 0.754 | 0.754 | 0 | 0/1 | - |
| L3 | EVENT_LOOP_COMPLETE | 14 | 14 | 14 | 1.0 | 1.0 | 0 | 0/0 | - |
| L4 | STAIRCASE_COMPLETE | 3 | 3 | 3 | 1.0 | 1.0 | 0 | 0/0 | - |

## 每层 × skill 诊断结论

| layer | skill | verdict | scored | correct | clusters | first-try correct | supported hypotheses | confirmation |
|---|---|---|---|---|---|---|---|---|
| L1 | spatial_near | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L1 | spatial_side | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L1 | object_recognition | boundary>=4 | 12 | 10 | 12 |  | - | - |
| L1 | object_location_at_time | boundary 3.5 | 5 | 5 | 5 |  | - | - |
| L1 | object_grounding | boundary<1 | 8 | 1 | 8 |  | - | - |
| L2 | sound_action_binding | boundary 3.5 | 8 | 7 | 8 |  | - | - |
| L2 | object_state_change | boundary 3.5 | 5 | 5 | 5 |  | - | - |
| L2 | action_temporal_order | boundary 1.5 | 12 | 4 | 12 |  | - | - |
| L2 | action_recognition | boundary>=4 | 12 | 11 | 12 |  | - | - |
| L2 | event_object_role | boundary>=4 | 12 | 11 | 12 |  | - | - |
| L2 | sound_anchored_spatial_near | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L2 | sound_anchored_spatial_side | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L2 | sound_movement_binding | boundary<1 | 8 | 5 | 8 |  | - | - |
| L3 | cross_event_integration | boundary>=4 | 12 | 12 | 12 |  | - | - |
| L3 | hidden_state_inference | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | spatial_state_integration | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | causal_prerequisite_reasoning | boundary 2.0 | 2 | 2 | 2 |  | - | - |
| L4 | goal_conditioned_planning | boundary 3.5 | 3 | 3 | 3 |  | - | - |

## L1 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 8 seconds into the clip, the camera wearer pours breadcrumbs into a bowl. What object are they pouring t |
| 2 | DIAG | object_grounding | bbox | coverage | - | correct | [0.517, 0.712, 0.583, 0.774] | 51.3, 72.5, 57.8, 80.0 | What is the bounding box of the lid of breadcrumb container in the first frame of the clip? |
| 3 | DIAG | object_recognition | single_choice | same_skill_new_event | - | correct | B | B | About 4 seconds into the clip, the camera wearer replaces a lid. What object are they replacing the lid on? |
| 4 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 7 seconds into the clip, the camera wearer picks up a container of breadcrumbs. Where do they place it? |
| 5 | DIAG | object_grounding | bbox | same_skill_new_event | - | wrong | [0.569, 0.826, 0.65, 0.915] | 41.9, 78.1, 48.9, 86.5 | What is the bounding box of the lid of breadcrumb container in the first frame of the clip? |
| 6 | DIAG | object_recognition | single_choice | same_skill_new_event | - | correct | C | C | About 6 seconds into the clip, the camera wearer pours flour. What object are they pouring the flour into? |
| 7 | DIAG | object_recognition | single_choice | same_skill_new_event | - | correct | B | B | About 5 seconds into the clip, the camera wearer pours flour from their hand. What object are they pouring the |
| 8 | DIAG | object_recognition | short_answer | same_skill_new_event | - | correct | Flour | flour | About 1 second into the clip, the camera wearer shapes the chicken and cheese mixture into a ball using their  |
| 9 | DIAG | object_recognition | short_answer | same_skill_new_event | - | correct | beaten egg | Egg | About 7 seconds into the clip, the camera wearer dips the potato chicken ball. What ingredient are they dippin |
| 10 | DIAG | object_location_at_time | single_choice | same_skill_new_event | - | correct | A | A | About 8 seconds into the clip, the camera wearer rolls the chicken ball in the flour bowl to coat it. Where do |
| 11 | DIAG | object_grounding | bbox | same_skill_new_event | - | wrong | [0.503, 0.628, 0.594, 0.719] | 47.0, 74.7, 58.8, 94.0 | What is the bounding box of the tupperware of flour in the first frame of the clip? |
| 12 | DIAG | object_recognition | short_answer | same_skill_new_event | - | correct | Breadcrumbs | breadcrumbs | About 6 seconds into the clip, after they dip the floured chicken ball into the egg bowl, the camera wearer sp |
| 13 | DIAG | object_location_at_time | single_choice | same_skill_new_event | - | correct | C | C | About 6 seconds into the clip, after they dip the floured chicken ball into the egg bowl, where does the camer |
| 14 | DIAG | object_grounding | bbox | same_skill_new_event | - | wrong | [0.382, 0.742, 0.622, 1.0] | 53.3, 69.4, 57.6, 75.2 | At the start of the clip, the camera wearer dips the floured chicken ball into the egg bowl. What is the bound |
| 15 | DIAG | object_recognition | short_answer | coverage | - | wrong | A grey bowl | Foil | About 6 seconds into the clip, the camera wearer scoops up tiny bits of potato chicken mixture. What object ar |
| 16 | DIAG | object_location_at_time | single_choice | same_skill_new_event | - | correct | A | A | About 5 seconds into the clip, the camera wearer picks up the uncoated potato chicken ball. Where do they pick |
| 17 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.52, 0.86, 0.62, 1.0] | 25.3, 90.1, 42.7, 98.6 | What is the bounding box of the tea towel in the first frame of the clip? |
| 18 | DIAG | object_recognition | short_answer | coverage | - | correct | a small grey bowl | bowl | About 7 seconds into the clip, while shaping the chicken and cheese mixture into a ball, the camera wearer ret |
| 19 | DIAG | object_grounding | bbox | same_skill_new_event | - | wrong | [0.503, 0.833, 0.559, 0.899] | 50.6, 73.0, 55.7, 77.8 | At the start of the clip, the camera wearer shapes the chicken and cheese mixture into a ball. What is the bou |
| 20 | DIAG | object_recognition | short_answer | coverage | - | correct | the bowl of beaten egg | bowl of eggs | About 5 seconds into the clip, the camera wearer retrieves the potato chicken ball. What object are they retri |
| 21 | DIAG | object_location_at_time | short_answer | same_skill_new_event | - | correct | the bowl of bread crumbs | the bowl of breadcrumbs | At the start of the clip, the camera wearer dips the floured chicken ball into the egg bowl. About 9 seconds i |
| 22 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.649, 0.809, 0.681, 0.844] | 48.9, 73.5, 54.7, 80.5 | At the start of the clip, the camera wearer dips the floured chicken ball into the egg bowl. What is the bound |
| 23 | DIAG | object_recognition | short_answer | coverage | - | wrong | Breadcrumbs | flour | About 5 seconds into the clip, the camera wearer sprinkles an ingredient over the potato chicken ball. What in |
| 24 | DIAG | object_recognition | short_answer | coverage | - | correct | Breadcrumbs | breadcrumbs | About 7 seconds into the clip, the camera wearer picks up an ingredient to sprinkle over the potato chicken ba |
| 25 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.47, 0.72, 0.51, 0.76] | 47.7, 74.5, 51.1, 80.5 | At the start of the clip, the camera wearer rolls the second chicken ball in the breadcrumbs bowl. What is the |

## L2 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | sound_action_binding | - | request_verification | - | evidence_unresolved | None | None |  |
| 2 | DIAG | action_temporal_order | single_choice | coverage | - | wrong | A | B | In the clip, what action does the camera wearer perform immediately before pouring the breadcrumbs into the bo |
| 3 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | In the clip, what action does the camera wearer perform involving the lid of breadcrumbs and the bowl? |
| 4 | DIAG | event_object_role | single_choice | coverage | - | correct | B | B | In the clip, when the camera wearer pours the breadcrumbs, what do they pour them into? |
| 5 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | In the clip, the camera wearer places the breadcrumbs container away in a cabinet. What action produces the co |
| 6 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | In the clip, the camera wearer picks up the breadcrumbs container to put it away. Where do they place it? |
| 7 | DIAG | action_temporal_order | single_choice | coverage | - | wrong | D | B | In the clip, the camera wearer places the breadcrumbs container away in a cabinet. What action do they perform |
| 8 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | C | C | In the clip, what action does the camera wearer perform involving the breadcrumbs container and the cabinet? |
| 9 | DIAG | event_object_role | single_choice | coverage | - | correct | C | C | In the clip, the camera wearer opens a cabinet to store an item away. What object do they place inside the cab |
| 10 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | In the clip, the camera wearer places the breadcrumbs container away in a cabinet. Which movement produces the |
| 11 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | In the clip, what action does the camera wearer perform immediately before they pour flour into the bowl for t |
| 12 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | In the clip, what action does the camera wearer perform involving the bag of flour and the cabinet? |
| 13 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | In the clip, the camera wearer reaches into a cabinet and secures some items in place to retrieve something be |
| 14 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | In the clip, what action does the camera wearer perform immediately after they pour flour into the bowl for th |
| 15 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | In the clip, what action does the camera wearer perform involving the flour and the bowl? |
| 16 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | C | C | In the clip, when the camera wearer pours the flour, what do they pour it into? |
| 17 | DIAG | sound_action_binding | single_choice | coverage | - | correct | C | C | In the clip, when the camera wearer shapes the chicken and potato mixture into a ball, which specific action p |
| 18 | DIAG | action_temporal_order | single_choice | coverage | - | wrong | B | A | In the clip, what action does the camera wearer perform immediately after they finish shaping the chicken and  |
| 19 | DIAG | action_recognition | short_answer | same_skill_new_event | - | correct | Rolls it into a ball with thei | rolling it into a ball | In the clip, what action does the camera wearer perform to change the shape of the chicken and potato mixture? |
| 20 | DIAG | event_object_role | short_answer | same_skill_new_event | - | correct | Chicken and cheese mixture | chicken and potato mixture | In the clip, what does the camera wearer roll into a ball using their hands? |
| 21 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | wrong | B | C | In the clip, shortly after the camera wearer shapes the chicken and cheese mixture into a ball, collision soun |
| 22 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | In the clip, the camera wearer empties a tupperware of flour into a bowl. Which specific action produces the c |
| 23 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | In the clip, while the camera wearer is rolling the chicken ball to coat it, they pick up a tupperware of flou |
| 24 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | In the clip, while the camera wearer is rolling the chicken ball to coat it, they pick up a tupperware of flou |
| 25 | DIAG | action_recognition | short_answer | same_skill_new_event | - | correct | rolls it between their palms | Rolls it in both hands | In the clip, what action does the camera wearer perform with the flour-coated chicken potato ball to improve i |
| 26 | DIAG | event_object_role | short_answer | same_skill_new_event | - | correct | Beaten eggs | egg | In the clip, the camera wearer dips the potato chicken ball into something and turns it around to coat it even |
| 27 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | In the clip, while the camera wearer is rolling the chicken ball to coat it, collision sounds are heard. Which |
| 28 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | In the clip, when the camera wearer dips the chicken ball into the egg bowl and rotates it, a brief collision  |
| 29 | DIAG | object_state_change | single_choice | coverage | - | correct | C | C | In the clip, the camera wearer dips the chicken ball into the egg bowl and then retrieves it. Where do they pl |
| 30 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | In the clip, what action does the camera wearer perform immediately after they retrieve the egg-coated chicken |
| 31 | DIAG | action_recognition | short_answer | same_skill_new_event | - | correct | Dips the floured chicken ball  | Dips the chicken ball into the | In the clip, what action does the camera wearer perform involving the chicken ball and the bowl of egg? |
| 32 | DIAG | event_object_role | short_answer | same_skill_new_event | - | correct | Breadcrumbs | Breadcrumbs | In the clip, the camera wearer places the egg-coated chicken ball into a bowl and sprinkles an ingredient over |
| 33 | DIAG | sound_movement_binding | single_choice | coverage | - | wrong | B | C | In the clip, the camera wearer dips the chicken ball into the egg bowl and then coats it with breadcrumbs. Dur |
| 34 | DIAG | sound_action_binding | short_answer | coverage | - | wrong | Closing a drawer | Returning the bowl of flour to | In the clip, the camera wearer picks up the uncoated potato chicken ball from the foil. What action, performed |
| 35 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | In the clip, the camera wearer picks up the uncoated potato chicken ball. Where do they pick it up from? |
| 36 | DIAG | action_temporal_order | single_choice | coverage | - | wrong | B | A | In the clip, what action does the camera wearer perform immediately before they pick up the uncoated potato ch |
| 37 | DIAG | action_recognition | short_answer | coverage | - | wrong | Places the uncoated potato chi | Picks it up | In the clip, what action does the camera wearer perform involving the uncoated potato chicken ball and the foi |
| 38 | DIAG | event_object_role | short_answer | coverage | - | correct | A potato chicken ball | Uncoated potato chicken ball | In the clip, the camera wearer returns the bowl of flour to the counter surface while picking up an item from  |
| 39 | DIAG | sound_movement_binding | single_choice | coverage | - | wrong | B | A | In the clip, the camera wearer picks up the uncoated potato chicken ball from the foil. Which movement produce |
| 40 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | In the clip, when the camera wearer shapes the chicken and cheese mixture into a ball, several collision sound |
| 41 | DIAG | action_temporal_order | single_choice | coverage | - | wrong | C | A | In the clip, what action does the camera wearer perform immediately after they finish shaping the chicken and  |
| 42 | DIAG | action_recognition | short_answer | coverage | - | correct | rolls it between their palms | Rolls it in both hands | In the clip, after adding more potato chicken mixture and flour to the ball, what action does the camera weare |
| 43 | DIAG | event_object_role | short_answer | same_skill_new_event | - | correct | a potato chicken ball | A potato chicken ball | In the clip, the camera wearer adds more mixture to an item held in their left hand and then rolls it between  |
| 44 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | In the clip, when the camera wearer shapes the chicken and cheese mixture into a ball, collision sounds are he |
| 45 | DIAG | sound_action_binding | single_choice | coverage | - | correct | B | B | In the clip, the camera wearer dips the potato chicken ball into the bowl of eggs and moves it around. Which s |
| 46 | DIAG | object_state_change | short_answer | coverage | - | correct | the bowl of bread crumbs | In the bowl of breadcrumbs | In the clip, the camera wearer dips the potato chicken ball into the bowl of eggs, retrieves it, and sprinkles |
| 47 | DIAG | action_temporal_order | single_choice | coverage | - | wrong | B | A | In the clip, what action does the camera wearer perform immediately after they retrieve the potato chicken bal |
| 48 | DIAG | action_recognition | short_answer | coverage | - | correct | dips the potato chicken ball i | dips the potato chicken ball i | In the clip, what action does the camera wearer perform involving the potato chicken ball and the bowl of eggs |
| 49 | DIAG | event_object_role | short_answer | coverage | - | correct | the floured chicken ball | potato chicken ball | In the clip, the camera wearer dips an item into the bowl of eggs and moves it around to coat it evenly. What  |
| 50 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | In the clip, the camera wearer dips the potato chicken ball into the bowl of eggs. Which movement produces the |
| 51 | DIAG | sound_action_binding | short_answer | coverage | - | correct | The camera wearer accidentally | scooping flour from the bowl | In the clip, the camera wearer sprinkles extra flour onto the potato chicken ball. What specific action produc |
| 52 | DIAG | action_temporal_order | single_choice | coverage | - | wrong | D | A | In the clip, what action does the camera wearer perform immediately after they sprinkle extra flour onto the p |
| 53 | DIAG | action_recognition | short_answer | coverage | - | correct | Sprinkles flour on the potato  | sprinkles flour over the potat | In the clip, what action does the camera wearer perform involving the flour and the potato chicken ball? |
| 54 | DIAG | event_object_role | short_answer | coverage | - | correct | Flour | Flour | In the clip, the camera wearer holds the potato chicken ball in their left hand and sprinkles an ingredient ov |
| 55 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | In the clip, the camera wearer sprinkles extra flour onto the potato chicken ball. Which movement produces the |
| 56 | DIAG | action_temporal_order | single_choice | coverage | - | wrong | B | A | In the clip, what action does the camera wearer perform immediately before they place the potato chicken ball  |
| 57 | DIAG | action_recognition | short_answer | coverage | - | correct | Coats the potato chicken ball  | Rolls the potato chicken ball  | In the clip, what action does the camera wearer perform involving the potato chicken ball and the bowl of brea |
| 58 | DIAG | event_object_role | short_answer | coverage | - | wrong | beaten egg | Breadcrumbs | In the clip, the camera wearer places the potato chicken ball into a bowl and rotates it to coat it evenly. Wh |

## L3 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | When the camera wearer places the grey bowl on the scale, what had happened to this bowl earlier in the clip? |
| 2 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | Before the camera wearer puts the cup away in the cabinet, what ingredient was poured out of it? |
| 3 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | When the camera wearer takes the bag of flour from the cabinet, what had they put into that same cabinet earli |
| 4 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | A | A | Before pouring the flour into the bowl, what did the camera wearer do to prepare the bowl? |
| 5 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | When the camera wearer rolls the chicken ball in the flour to coat it, where did they get that flour from earl |
| 6 | DIAG | causal_prerequisite_reasoning | single_choice | same_skill_new_event | - | correct | A | A | Before the camera wearer rolls the chicken ball to coat it, what ingredient was added to the grey bowl? |
| 7 | DIAG | cross_event_integration | short_answer | coverage | - | correct | Flour and beaten egg | flour and egg | When the camera wearer rolls the chicken ball in the bowl of breadcrumbs, what had they already coated this ch |
| 8 | DIAG | cross_event_integration | short_answer | same_skill_new_event | - | correct | flour | Flour | When the camera wearer dips the chicken ball in the bowl of egg, what had they already coated this chicken bal |
| 9 | DIAG | cross_event_integration | short_answer | coverage | - | correct | Coated them with flour, egg, a | coated them in egg and breadcr | When the camera wearer picks up the next uncoated chicken ball, what had they already done to the previous chi |
| 10 | DIAG | cross_event_integration | short_answer | coverage | - | correct | Coating it with flour, egg, an | Coated it in egg and breadcrum | When the camera wearer picks up the uncoated chicken ball from the foil, what had they just finished doing to  |
| 11 | DIAG | cross_event_integration | short_answer | coverage | - | correct | coating it with breadcrumbs an | Coating it with breadcrumbs | When the camera wearer shapes the second chicken mixture into a ball, what had they just finished doing to the |
| 12 | DIAG | cross_event_integration | short_answer | coverage | - | correct | Flour and egg | flour and egg | When the camera wearer sprinkles extra flour over the chicken ball, what had they already coated this chicken  |
| 13 | DIAG | cross_event_integration | short_answer | same_skill_new_event | - | correct | Flour and egg | flour and egg | When the camera wearer places the second chicken ball into the bowl of breadcrumbs, what ingredients had they  |
| 14 | DIAG | cross_event_integration | short_answer | same_skill_new_event | - | correct | Flour | Flour | When the camera wearer dips the second chicken ball into the bowl of egg, what ingredient had they already coa |

## L4 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | B | B | Based on the progress shown in the clip, what is the next step for the task the camera wearer is doing? |
| 2 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | C | C | Based on the progress shown in the clip, what is the next step for the task the camera wearer is doing? |
| 3 | DIAG | goal_conditioned_planning | plan | coverage | - | correct | ['Finish moulding the chicken  | 1. Shape a second chicken ball | What are the remaining stages, in order, for the task the camera wearer is doing? |

## Gemini 用量

| role | calls | errors | tok_in | tok_out | tok_think |
|---|---|---|---|---|---|
| examiner | 112 | 0 | 3091090 | 69883 | 363271 |
| judge | 42 | 0 | 12936 | 2443 | 8205 |
| solver | 297 | 0 | 1284192 | 5394 | 0 |
