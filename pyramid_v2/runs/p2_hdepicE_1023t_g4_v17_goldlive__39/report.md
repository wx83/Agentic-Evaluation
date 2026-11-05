# pyramid2 run `p2_hdepicE_1023t_g4_v17_goldlive__39`

dataset hdepic_e · videos 1 · examiner `gcp/google/gemini-3.1-pro-preview` · solver `gcp/google/gemini-4-argon` · n_per_layer 200 · seed 1023 · prompt physical-mental-draft2-hdepic-e+v16sg

**结果为 provisional**:gold = Examiner 的 proposed_reference_answer,未经人工核验;open/plan 题由 Gemini judge 判。

## 每层概览

| layer | stop | turns | scored | correct | raw acc | cluster-dedup acc | follow-up | invalid/unresolved | confirmation |
|---|---|---|---|---|---|---|---|---|---|
| L1 | EVENT_LOOP_COMPLETE | 14 | 12 | 10 | 0.833 | 0.833 | 0 | 0/2 | - |
| L2 | EVENT_LOOP_COMPLETE | 44 | 44 | 40 | 0.909 | 0.909 | 0 | 0/0 | - |
| L3 | EVENT_LOOP_COMPLETE | 13 | 13 | 13 | 1.0 | 1.0 | 0 | 0/0 | - |
| L4 | STAIRCASE_COMPLETE | 5 | 5 | 4 | 0.8 | 0.8 | 0 | 0/0 | - |

## 每层 × skill 诊断结论

| layer | skill | verdict | scored | correct | clusters | first-try correct | supported hypotheses | confirmation |
|---|---|---|---|---|---|---|---|---|
| L1 | spatial_near | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L1 | spatial_side | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L1 | object_recognition | boundary>=4 | 8 | 8 | 8 |  | - | - |
| L1 | object_location_at_time | boundary 2.0 | 2 | 2 | 2 |  | - | - |
| L1 | object_grounding | boundary 1.5 | 2 | 0 | 2 |  | - | - |
| L2 | sound_action_binding | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | object_state_change | boundary 2.0 | 2 | 2 | 2 |  | - | - |
| L2 | action_temporal_order | boundary>=4 | 10 | 9 | 10 |  | - | - |
| L2 | action_recognition | boundary>=4 | 10 | 9 | 10 |  | - | - |
| L2 | event_object_role | boundary>=4 | 10 | 10 | 10 |  | - | - |
| L2 | sound_anchored_spatial_near | boundary 1.5 | 3 | 1 | 3 |  | - | - |
| L2 | sound_anchored_spatial_side | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L2 | sound_movement_binding | boundary 2.5 | 3 | 3 | 3 |  | - | - |
| L3 | cross_event_integration | boundary>=4 | 12 | 12 | 12 |  | - | - |
| L3 | hidden_state_inference | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | spatial_state_integration | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | causal_prerequisite_reasoning | boundary 1.0 | 1 | 1 | 1 |  | - | - |
| L4 | goal_conditioned_planning | boundary 2.75 | 5 | 4 | 5 |  | - | - |

## L1 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | At the start of the clip, as the person prepares to open the can of chickpeas, what object are they holding in |
| 2 | DIAG | object_recognition | single_choice | same_skill_new_event | - | correct | A | A | About 6 seconds into the clip, during the sound of running water splashing into the metal can, what object is  |
| 3 | DIAG | object_location_at_time | single_choice | coverage | - | correct | B | B | About 3 seconds into the clip, the sound of running water splashing into the metal can begins. Just before thi |
| 4 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.472, 0.622, 0.656, 0.854] | 47.2, 78.8, 69.7, 100.2 | About half a second into the clip, the sound of running water splashing into the metal can begins. In the firs |
| 5 | DIAG | object_recognition | single_choice | same_skill_new_event | - | correct | A | A | About 4 seconds into the clip, as the person tips the container to pour the liquid down the sink drain, what o |
| 6 | DIAG | object_recognition | single_choice | same_skill_new_event | - | correct | A | A | About 4 seconds into the clip, as the person holds an object under the running tap water to rinse it out, what |
| 7 | DIAG | object_recognition | short_answer | same_skill_new_event | - | correct | a colander | colander | About 2 seconds into the clip, as the person holds an object in both hands and swirls the chickpeas around in  |
| 8 | DIAG | object_recognition | - | request_verification | - | evidence_unresolved | None | None |  |
| 9 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 2 seconds into the clip, the person dumps the rinsed chickpeas from the colander onto paper towels. At t |
| 10 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.22, 0.66, 0.61, 0.98] | 20.9, 46.3, 35.2, 68.2 | In the first frame of the clip, what is the bounding box of the kitchen roll? |
| 11 | DIAG | object_recognition | short_answer | same_skill_new_event | - | correct | a paper towel | kitchen paper | About 8 seconds into the clip, as the person gently rubs or pats the chickpeas to dry them, what object are th |
| 12 | DIAG | object_recognition | short_answer | coverage | - | correct | Chickpea skin (hull) | loose skin | About 6 seconds into the clip, as the person picks up something with their right hand and places it on the cou |
| 13 | DIAG | object_recognition | short_answer | same_skill_new_event | - | correct | chickpeas | a chickpea | About 9 seconds into the clip, as the person uses their right hand to peel off the loose skin, what object are |
| 14 | DIAG | object_recognition | - | request_verification | - | evidence_unresolved | None | None |  |

## L2 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | sound_action_binding | single_choice | coverage | - | correct | C | C | Which of the following actions produces the sound of metal being cut open heard in the clip? |
| 2 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | When the person opens the can of chickpeas, in what order do the following actions occur? |
| 3 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | What action does the person perform to open the can of chickpeas? |
| 4 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | What tool does the person use to open the can of chickpeas? |
| 5 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | correct | A | A | When the person uses the can opener, at the moment the sound of cutting or chopping is heard, which of the fol |
| 6 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | correct | A | A | Which of the following actions produces the sound of running water splashing into a metal container heard in t |
| 7 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | After rinsing the can under the running water, where does the person put the can down? |
| 8 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | A | A | When the person drains the chickpeas and rinses the can, in what order do the following actions occur? |
| 9 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | When the sound of running water splashing into the metal can is heard, what does the person do with the can? |
| 10 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | A | A | When the person holds an object under the running water to rinse it out and then empties the water into the si |
| 11 | DIAG | sound_anchored_spatial_near | single_choice | same_skill_new_event | - | wrong | D | B | When the sound of running water splashing into the metal can is heard, which of the following objects is neare |
| 12 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | B | B | Which of the following object movements is associated with the sound of running water splashing into the metal |
| 13 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | correct | A | A | Which of the following actions produces the distinct sound of liquid being poured out, heard over the running  |
| 14 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | A | A | Before the person tips the can to pour the aquafaba liquid down the sink drain, in what order do the following |
| 15 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | What action does the person perform to empty the chickpeas and aquafaba from the can? |
| 16 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | A | A | When the person pours the chickpeas into the colander, what container is being tipped? |
| 17 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | wrong | B | A | When the person tips the can to pour the liquid down the sink drain, at the moment the sound of liquid pouring |
| 18 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | correct | A | A | Which of the following object movements is associated with the distinct sound of liquid being poured out, hear |
| 19 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | A | A | When the person runs tap water into the can to rinse the remaining liquid, in what order do the following acti |
| 20 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | What action does the person perform to get water into the can to rinse it? |
| 21 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | A | A | When the person runs tap water into an object to rinse out the remaining liquid, which object is being rinsed? |
| 22 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | correct | A | A | Which of the following actions produces the rattling sound of small items hitting a plastic container heard in |
| 23 | DIAG | action_temporal_order | short_answer | same_skill_new_event | - | correct | Turning off the faucet with th | adjust the tap | When the person rinses the chickpeas in the colander, what action do they perform immediately after transferri |
| 24 | DIAG | action_recognition | short_answer | same_skill_new_event | - | correct | swirls the colander in a circu | Swirling the colander | What action does the person perform to rinse the chickpeas under the running water? |
| 25 | DIAG | event_object_role | short_answer | same_skill_new_event | - | correct | A white colander | colander | When the person swirls the chickpeas around to rinse them under the running water, what container holds the ch |
| 26 | DIAG | sound_action_binding | short_answer | same_skill_new_event | - | correct | Placing the colander back into | putting the colander in the si | When the person dumps the rinsed chickpeas from the colander onto paper towels, what action produces the sound |
| 27 | DIAG | object_state_change | single_choice | same_skill_new_event | - | correct | A | A | When the person tips the colander to empty the rinsed chickpeas, where do they pour the chickpeas? |
| 28 | DIAG | action_temporal_order | short_answer | same_skill_new_event | - | correct | Return the colander to the sin | Replacing the colander in the  | When the person dumps the rinsed chickpeas from the colander onto the paper towels, what action do they perfor |
| 29 | DIAG | action_recognition | short_answer | same_skill_new_event | - | correct | Dumps them out of the colander | tips the colander | What action does the person perform to transfer the rinsed chickpeas from the colander onto the paper towels? |
| 30 | DIAG | event_object_role | short_answer | same_skill_new_event | - | correct | A colander | colander | When the person dumps the rinsed chickpeas onto the paper towels, what container are the chickpeas poured out  |
| 31 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | correct | A | A | When the person dumps the rinsed chickpeas from the colander onto the paper towels, which of the following obj |
| 32 | DIAG | action_temporal_order | short_answer | same_skill_new_event | - | correct | folds the kitchen paper over t | Fold the paper towel over the  | When the person dries the chickpeas with the paper towel, what action do they perform immediately after pickin |
| 33 | DIAG | action_recognition | short_answer | same_skill_new_event | - | correct | They fold the paper over the c | Folds it over the chickpeas an | What action does the person perform with the kitchen paper to dry the chickpeas? |
| 34 | DIAG | event_object_role | short_answer | same_skill_new_event | - | correct | paper towel | Kitchen paper | When the person folds a material over the chickpeas and gently presses down to dry them, what material do they |
| 35 | DIAG | action_temporal_order | short_answer | coverage | - | correct | places the loose skin on the c | Places the loose skin down on  | When the person holds a chickpea and pinches it to pull away the loose skin for the first time, what action do |
| 36 | DIAG | action_recognition | short_answer | coverage | - | correct | Pinching and peeling them off | pinches the chickpeas | When the person handles the individual chickpeas, what action do they perform to remove the loose skins? |
| 37 | DIAG | event_object_role | short_answer | coverage | - | correct | directly on the wooden counter | On the counter | When the person pinches and peels the individual chickpeas to remove their loose skins, where do they place th |
| 38 | DIAG | action_temporal_order | short_answer | same_skill_new_event | - | wrong | Peel the skin off the chickpea | picks up a chickpea | When the person uses their left hand to scoop the loose skin into a neat pile, what action do they perform imm |
| 39 | DIAG | action_recognition | short_answer | same_skill_new_event | - | wrong | places them on the paper towel | scoops them into a pile | What action does the person perform to organize the loose skins they have placed on the counter? |
| 40 | DIAG | event_object_role | short_answer | same_skill_new_event | - | correct | a small pile | A pile | When the person scoops the loose skins on the counter, what do they form them into? |
| 41 | DIAG | sound_action_binding | short_answer | coverage | - | correct | Dropping chickpeas on the meta | Placing the scooped chickpeas  | When the person moves the dried chickpeas from the paper towels onto the baking tray, what specific action pro |
| 42 | DIAG | action_temporal_order | short_answer | same_skill_new_event | - | correct | Picks up two loose chickpeas f | scoops up the chickpeas that h | When the person moves the dried chickpeas from the paper towels onto the baking tray, what action do they perf |
| 43 | DIAG | action_recognition | short_answer | same_skill_new_event | - | correct | Picks up the paper towel and p | Lifts the kitchen paper and ti | What action does the person perform to transfer the dried chickpeas onto the baking tray? |
| 44 | DIAG | event_object_role | short_answer | same_skill_new_event | - | correct | A black baking tray | A baking tray | When the person lifts and tips the kitchen paper to move the dried chickpeas, what object do they transfer the |

## L3 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | Before the camera wearer runs tap water into the can, what was done to it? |
| 2 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | Before the camera wearer runs tap water into the can, what was done to it? |
| 3 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | B | B | Why is the camera wearer able to pour liquid out of the can? |
| 4 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | Before the camera wearer runs water over the chickpeas in the colander, what was the running water used for? |
| 5 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | Before the camera wearer rinses the chickpeas in the colander under running water, what was done with the can? |
| 6 | DIAG | cross_event_integration | short_answer | coverage | - | correct | The metal can | the can | Before the camera wearer runs water over the chickpeas in the colander, what was the running water used to rin |
| 7 | DIAG | cross_event_integration | short_answer | coverage | - | correct | Rinsed under running tap water | It was rinsed with water. | Before the chickpeas are rinsed in the colander, what was done to the empty can? |
| 8 | DIAG | cross_event_integration | short_answer | coverage | - | correct | Rinsed with water in the sink | They were rinsed under running | Before the chickpeas are tipped out of the colander onto the paper towels, what was done to them? |
| 9 | DIAG | cross_event_integration | short_answer | coverage | - | correct | Rinsing and draining the chick | To rinse the chickpeas under r | Before the camera wearer tips the chickpeas out of the colander onto the kitchen paper, what was the colander  |
| 10 | DIAG | cross_event_integration | short_answer | coverage | - | correct | They were rinsed in a colander | They were rinsed under running | Before the chickpeas are tipped onto the kitchen paper, what was done to them? |
| 11 | DIAG | cross_event_integration | short_answer | coverage | - | correct | Dried with kitchen paper | They were dried with paper tow | Before the camera wearer pinches the chickpeas to remove their skins, what was done to them? |
| 12 | DIAG | cross_event_integration | short_answer | coverage | - | correct | pinching the chickpeas | Pinching them | Before the camera wearer picks loose skins from the chickpeas on the baking tray, what action was used to remo |
| 13 | DIAG | cross_event_integration | short_answer | coverage | - | correct | Loose skins | Their loose skins | Before the chickpeas are transferred to the baking tray, what was removed from them? |

## L4 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | A | A | What is the next step the camera wearer should take to complete the task they are doing? |
| 2 | DIAG | goal_conditioned_planning | single_choice | same_skill_new_event | - | correct | C | C | What is the next step the camera wearer should take to complete the task they are doing? |
| 3 | DIAG | goal_conditioned_planning | plan | coverage | - | wrong | ['Remove the loose skins from  | 1. Remove any loose skins from | What are the remaining stages, in order, to complete the task the camera wearer is doing? |
| 4 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | C | C | What is the next step the camera wearer should take to complete the task they are doing? |
| 5 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | B | B | What is the next step the camera wearer should take to complete the task they are doing? |

## Gemini 用量

| role | calls | errors | tok_in | tok_out | tok_think |
|---|---|---|---|---|---|
| examiner | 80 | 0 | 2116868 | 49940 | 231317 |
| judge | 45 | 0 | 13781 | 2645 | 6973 |
| solver | 222 | 0 | 1160187 | 3977 | 0 |
