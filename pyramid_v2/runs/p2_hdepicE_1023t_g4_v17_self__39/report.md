# pyramid2 run `p2_hdepicE_1023t_g4_v17_self__39`

dataset hdepic_e · videos 1 · examiner `gcp/google/gemini-3.1-pro-preview` · solver `gcp/google/gemini-4-argon` · n_per_layer 200 · seed 1023 · prompt physical-mental-draft2-hdepic-e+v16sg

**结果为 provisional**:gold = Examiner 的 proposed_reference_answer,未经人工核验;open/plan 题由 Gemini judge 判。

## 每层概览

| layer | stop | turns | scored | correct | raw acc | cluster-dedup acc | follow-up | invalid/unresolved | confirmation |
|---|---|---|---|---|---|---|---|---|---|
| L1 | EVENT_LOOP_COMPLETE | 14 | 14 | 11 | 0.786 | 0.786 | 0 | 0/0 | - |
| L2 | EVENT_LOOP_COMPLETE | 44 | 44 | 39 | 0.886 | 0.886 | 0 | 0/0 | - |
| L3 | EVENT_LOOP_COMPLETE | 13 | 13 | 11 | 0.846 | 0.846 | 0 | 0/0 | - |
| L4 | STAIRCASE_COMPLETE | 6 | 5 | 4 | 0.8 | 0.8 | 0 | 1/0 | - |

## 每层 × skill 诊断结论

| layer | skill | verdict | scored | correct | clusters | first-try correct | supported hypotheses | confirmation |
|---|---|---|---|---|---|---|---|---|
| L1 | spatial_near | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L1 | spatial_side | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L1 | object_recognition | boundary>=4 | 10 | 9 | 10 |  | - | - |
| L1 | object_location_at_time | boundary 2.0 | 2 | 2 | 2 |  | - | - |
| L1 | object_grounding | boundary 1.5 | 2 | 0 | 2 |  | - | - |
| L2 | sound_action_binding | boundary 3.25 | 6 | 5 | 6 |  | - | - |
| L2 | object_state_change | boundary 2.0 | 2 | 2 | 2 |  | - | - |
| L2 | action_temporal_order | boundary>=4 | 10 | 10 | 10 |  | - | - |
| L2 | action_recognition | boundary>=4 | 10 | 9 | 10 |  | - | - |
| L2 | event_object_role | boundary>=4 | 10 | 9 | 10 |  | - | - |
| L2 | sound_anchored_spatial_near | boundary 1.5 | 3 | 1 | 3 |  | - | - |
| L2 | sound_anchored_spatial_side | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L2 | sound_movement_binding | boundary 2.5 | 3 | 3 | 3 |  | - | - |
| L3 | cross_event_integration | boundary>=4 | 12 | 10 | 12 |  | - | - |
| L3 | hidden_state_inference | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | spatial_state_integration | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | causal_prerequisite_reasoning | boundary 1.0 | 1 | 1 | 1 |  | - | - |
| L4 | goal_conditioned_planning | boundary 2.75 | 5 | 4 | 5 |  | - | - |

## L1 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | object_recognition | single_choice | coverage | - | correct | C | C | At the start of the clip, as the person opens the can of chickpeas, what object is held in the right hand? |
| 2 | DIAG | object_recognition | single_choice | same_skill_new_event | - | correct | B | B | About 8 seconds into the clip, as the sound of running water splashing into the metal can is heard, what objec |
| 3 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | At the start of the clip, as the sound of running water splashing into the metal can is heard, where is the co |
| 4 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.472, 0.677, 0.652, 0.85] | 47.2, 78.8, 69.7, 100.2 | In the first frame of the clip, about half a second before the sound of running water splashing into the metal |
| 5 | DIAG | object_recognition | single_choice | same_skill_new_event | - | correct | A | A | About 4 seconds into the clip, as the person tips an object to pour the aquafaba liquid down the sink drain, w |
| 6 | DIAG | object_recognition | single_choice | same_skill_new_event | - | correct | A | A | About 4 seconds into the clip, as the person rinses an object out, what object is held under the running water |
| 7 | DIAG | object_recognition | short_answer | same_skill_new_event | - | correct | a white colander | colander | About 1 second into the clip, as the person adjusts the tap using the right hand, what object is held in the l |
| 8 | DIAG | object_recognition | short_answer | same_skill_new_event | - | correct | the paper towel roll | roll of kitchen paper | About 1 second into the clip, as the person pulls out two more sheets, what object is held steady with the lef |
| 9 | DIAG | object_location_at_time | single_choice | same_skill_new_event | - | correct | A | A | At the start of the clip, before the person dumps the rinsed chickpeas from the colander, where is the piece o |
| 10 | DIAG | object_grounding | bbox | same_skill_new_event | - | wrong | [0.19, 0.68, 0.62, 1.0] | 20.9, 46.3, 35.2, 68.2 | In the first frame of the clip, before the person dumps the rinsed chickpeas from the colander onto paper towe |
| 11 | DIAG | object_recognition | short_answer | coverage | - | correct | paper towel | kitchen paper | About 8 seconds into the clip, as the person uses the left hand to fold over an object so that it is on top of |
| 12 | DIAG | object_recognition | short_answer | coverage | - | correct | chickpea skin | loose skin | About 6 seconds into the clip, as the person picks up an object with the right hand and places it on the count |
| 13 | DIAG | object_recognition | short_answer | coverage | - | correct | chickpeas | a chickpea | About 9 seconds into the clip, as the person uses the right hand to peel off the loose skin, what object is pi |
| 14 | DIAG | object_recognition | short_answer | coverage | - | wrong | chickpeas | loose skin | About 4 seconds into the clip, as the person uses the right hand to pick up an object and place it into the up |

## L2 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | When the camera wearer turns the blade of the can opener to open the can, what sound is heard? |
| 2 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | When the camera wearer opens the can of chickpeas, what do they do immediately before they start turning the b |
| 3 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | What action does the camera wearer perform to open the can of chickpeas? |
| 4 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | When the camera wearer opens the can of chickpeas, what tool do they use? |
| 5 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | correct | B | B | When the camera wearer opens the container, at the moment a cutting or chopping sound is heard, which of the f |
| 6 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | correct | A | A | During the clip, which action produces the sound of running water splashing into the metal can? |
| 7 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | During the clip, the sound of running water splashing into the metal can is heard. Where does the camera weare |
| 8 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | C | C | During the clip, the sound of running water splashing into the metal can is heard. What does the camera wearer |
| 9 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | During the clip, the second time the camera wearer holds the can under the running water, what action are they |
| 10 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | A | A | During the clip, the sound of running water splashing into the metal can is heard. When the camera wearer hold |
| 11 | DIAG | sound_anchored_spatial_near | single_choice | same_skill_new_event | - | wrong | D | B | During the clip, the sound of running water splashing into the metal can is heard. At the moment that sound is |
| 12 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | During the clip, the sound of running water splashing into the metal can is heard. Which object is moved to th |
| 13 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | correct | A | A | During the clip, when the camera wearer tips the can to drain the chickpeas, what sound is produced by this ac |
| 14 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | C | C | During the clip, what does the camera wearer do immediately after they tip the can to drain the aquafaba? |
| 15 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | During the clip, how does the camera wearer empty the chickpeas from the can into the colander? |
| 16 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | A | A | During the clip, when the camera wearer tips the can to drain the aquafaba, into which object are the chickpea |
| 17 | DIAG | sound_anchored_spatial_near | single_choice | same_skill_new_event | - | wrong | B | A | During the clip, when the camera wearer tips the can to drain the liquid, at the moment the sound of water is  |
| 18 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | correct | A | A | During the clip, when the camera wearer drains the liquid, the sound of water is heard. Which object is being  |
| 19 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | A | A | During the clip, what does the camera wearer do immediately after they first hold the can under the running wa |
| 20 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | During the clip, what action does the camera wearer perform to put water into the can the first time? |
| 21 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | A | A | During the clip, when the camera wearer first uses the running water to rinse something out, what object do th |
| 22 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | correct | A | A | During the clip, which action produces the sound of plastic colliding? |
| 23 | DIAG | action_temporal_order | short_answer | same_skill_new_event | - | correct | adjust the tap | adjust the tap | During the clip, as the person pours the chickpeas from the can into a colander and runs them under the water, |
| 24 | DIAG | action_recognition | short_answer | same_skill_new_event | - | correct | shakes the colander | swirl the colander | During the clip, what action does the camera wearer perform to rinse the chickpeas under the running water? |
| 25 | DIAG | event_object_role | short_answer | same_skill_new_event | - | correct | a white colander | colander | During the clip, what object does the camera wearer hold to rinse the chickpeas under the running water? |
| 26 | DIAG | sound_action_binding | short_answer | same_skill_new_event | - | correct | putting the colander in the si | putting the colander in the si | During the clip, immediately after the person dumps the rinsed chickpeas from the colander onto paper towels,  |
| 27 | DIAG | object_state_change | single_choice | same_skill_new_event | - | correct | A | A | During the clip, when the camera wearer tips the colander to empty the chickpeas, where are the chickpeas pour |
| 28 | DIAG | action_temporal_order | short_answer | same_skill_new_event | - | correct | pick up the colander of chickp | picks up the colander | During the clip, what action does the camera wearer perform immediately before they tip the colander to empty  |
| 29 | DIAG | action_recognition | short_answer | same_skill_new_event | - | correct | By tilting the colander and sh | tips the colander | During the clip, how does the camera wearer empty the chickpeas from the colander onto the paper towels? |
| 30 | DIAG | event_object_role | short_answer | same_skill_new_event | - | correct | a colander | a colander | During the clip, when the camera wearer empties the rinsed chickpeas onto the paper towels, what object do the |
| 31 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | correct | A | A | During the clip, immediately after the person dumps the rinsed chickpeas onto the paper towels, a metal or pla |
| 32 | DIAG | action_temporal_order | short_answer | same_skill_new_event | - | correct | peels the top layer of the pap | unfold the kitchen roll | During the clip, what action does the camera wearer perform immediately after they finish pressing down and ta |
| 33 | DIAG | action_recognition | short_answer | same_skill_new_event | - | correct | Pats down the paper towel with | presses down and taps the chic | During the clip, what action does the camera wearer perform to dry the chickpeas after folding the paper towel |
| 34 | DIAG | event_object_role | short_answer | same_skill_new_event | - | correct | chickpeas | chickpeas | During the clip, what object does the camera wearer dry by folding a paper towel over it and pressing down? |
| 35 | DIAG | action_temporal_order | short_answer | same_skill_new_event | - | correct | places the peeled skin on the  | places the loose skin down on  | During the clip, what action does the camera wearer perform immediately after they first pinch a chickpea to p |
| 36 | DIAG | action_recognition | short_answer | same_skill_new_event | - | correct | peels them off with their fing | pinches the chickpeas to peel  | During the clip, what action does the camera wearer perform to remove the loose skins from the chickpeas? |
| 37 | DIAG | event_object_role | short_answer | same_skill_new_event | - | correct | chickpeas | chickpeas | During the clip, what object does the camera wearer hold and pinch with their fingers to pull away the loose s |
| 38 | DIAG | action_temporal_order | short_answer | same_skill_new_event | - | correct | picking up the chickpeas | picks up a chickpea | During the clip, what action does the camera wearer perform immediately after they use their left hand to scoo |
| 39 | DIAG | action_recognition | short_answer | coverage | - | wrong | Places them on the paper towel | places them on the counter | During the clip, what action does the camera wearer perform to dispose of the loose skins they have removed fr |
| 40 | DIAG | event_object_role | short_answer | same_skill_new_event | - | wrong | on the paper towel to the left | on the counter | During the clip, when the camera wearer disposes of the loose skins they have removed from the chickpeas, wher |
| 41 | DIAG | sound_action_binding | short_answer | same_skill_new_event | - | wrong | the chickpeas hitting the baki | scooping up the stray chickpea | During the clip, after the camera wearer tips the chickpeas from the kitchen paper onto the baking tray, a met |
| 42 | DIAG | action_temporal_order | short_answer | coverage | - | correct | places the kitchen paper on th | places the kitchen paper down  | During the clip, what action does the camera wearer perform immediately after they tip the chickpeas from the  |
| 43 | DIAG | action_recognition | short_answer | coverage | - | correct | by lifting the kitchen paper b | lifts the kitchen paper and ti | During the clip, how does the camera wearer move the chickpeas from the kitchen paper to the baking tray? |
| 44 | DIAG | event_object_role | short_answer | coverage | - | correct | baking tray | a baking tray | During the clip, when the camera wearer lifts the kitchen paper by its corners to tip the chickpeas, what obje |

## L3 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | Before the camera wearer holds the can under running water to rinse it, what was done to the can? |
| 2 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | When the running water splashes into the metal can, what had been done to the can earlier in the clip? |
| 3 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | C | C | What earlier action was necessary to be able to pour liquid out of the can? |
| 4 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | B | B | Before the person runs water over the chickpeas in the colander, what was the running water used to rinse? |
| 5 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | C | C | Before the person rinses the chickpeas in the colander under the running water, what was done with the empty c |
| 6 | DIAG | cross_event_integration | short_answer | same_event_new_format | - | correct | The metal can | the can | Before the person runs water over the chickpeas in the colander, what was the running water used to rinse? |
| 7 | DIAG | cross_event_integration | short_answer | coverage | - | correct | the metal can | The empty can | Before the person rinses the chickpeas in the colander, what object is rinsed out under the tap? |
| 8 | DIAG | cross_event_integration | short_answer | coverage | - | correct | They were rinsed and drained u | They were rinsed under running | Before the person tips the chickpeas out of the colander onto the paper towels, what was done to the chickpeas |
| 9 | DIAG | cross_event_integration | short_answer | same_skill_new_event | - | correct | rinsing and draining the chick | To rinse the chickpeas under r | Before the person tips the chickpeas out of the colander onto the paper towels, what was the colander used for |
| 10 | DIAG | cross_event_integration | short_answer | same_skill_new_event | - | wrong | In the colander under the runn | They were swirled and tossed u | Before the person tips the chickpeas out of the colander onto the paper towels, how were they rinsed? |
| 11 | DIAG | cross_event_integration | short_answer | same_skill_new_event | - | correct | Dried them with a paper towel | They were placed on paper towe | Before the person pinches the chickpeas to remove their loose skins, what was done to the chickpeas? |
| 12 | DIAG | cross_event_integration | short_answer | same_skill_new_event | - | wrong | peeled off with their fingers | They were pinched individually | Before the person picks off the remaining loose skins from the chickpeas on the baking tray, how were the skin |
| 13 | DIAG | cross_event_integration | short_answer | same_skill_new_event | - | correct | loose skins and excess water | The loose skins | Before the person tips the chickpeas onto the baking tray, what was removed from the chickpeas? |

## L4 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | goal_conditioned_planning | single_choice | coverage | - | item_invalid | None | C | For the task the camera wearer is doing, what is the next step to take right after the clip ends? |
| 2 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | B | B | For the task the camera wearer is doing, what is the next step to take right after the clip ends? |
| 3 | DIAG | goal_conditioned_planning | single_choice | same_skill_new_event | - | correct | C | C | For the task the camera wearer is doing, what is the next step to take right after the clip ends? |
| 4 | DIAG | goal_conditioned_planning | plan | same_skill_new_event | - | wrong | ['Remove the loose skins from  | 1. Peel the loose skins off th | For the task the camera wearer is doing, what are the remaining stages, in order? |
| 5 | DIAG | goal_conditioned_planning | single_choice | same_skill_new_event | - | correct | C | C | For the task the camera wearer is doing, what is the next step to take right after the clip ends? |
| 6 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | B | B | For the task the camera wearer is doing, what is the next step to take right after the clip ends? |

## Gemini 用量

| role | calls | errors | tok_in | tok_out | tok_think |
|---|---|---|---|---|---|
| examiner | 83 | 0 | 2203809 | 52281 | 267941 |
| judge | 48 | 0 | 14918 | 2842 | 7712 |
| solver | 228 | 0 | 1166184 | 4056 | 0 |
