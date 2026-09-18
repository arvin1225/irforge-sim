# Focused literature survey

## Infrared small-target detection

- Zhang et al., **ISNet: Shape Matters for Infrared Small Target Detection**, CVPR 2022. Introduces IRSTD-1k and emphasizes dim, low-SNR, few-pixel targets and clutter. Relevance: motivates target-level localization and false-alarm metrics rather than image accuracy alone. https://openaccess.thecvf.com/content/CVPR2022/html/Zhang_ISNet_Shape_Matters_for_Infrared_Small_Target_Detection_CVPR_2022_paper.html
- Liu et al., **Infrared Small Target Detection with Scale and Location Sensitivity**, CVPR 2024. Shows that target scale and location-sensitive losses matter even with a simple model. Relevance: motivates explicit localization tolerance and scale-stratified failure analysis. https://openaccess.thecvf.com/content/CVPR2024/html/Liu_Infrared_Small_Target_Detection_with_Scale_and_Location_Sensitivity_CVPR_2024_paper.html
- Lu et al., **Rethinking Generalizable Infrared Small Target Detection: A Real-scene Benchmark and Cross-view Representation Learning**, IEEE TGRS 2025. Treats sensor and scene variation as a cross-domain generalization problem and releases the RealScene-ISTD benchmark. Relevance: reinforces that controlled synthetic failure boundaries require later cross-dataset testing on measured imagery. https://arxiv.org/abs/2504.16487
- Yuan et al., **Seeing Through the Noise**, CVPR 2026. Treats noise suppression as a central source of false alarms. Relevance: supports testing noise interactions, while IRForge differs by studying controlled composition shift and rejection instead of proposing a feature pyramid. https://openaccess.thecvf.com/content/CVPR2026/html/Yuan_Seeing_Through_the_Noise_Improving_Infrared_Small_Target_Detection_and_CVPR_2026_paper.html
- Lu et al., **Degraded Infrared Small Object Detection via Degradation-Adapted Physics-Guided Restoration**, 2026 preprint. Couples degradation identification with physics-guided restoration across multiple corruption types. Relevance: supports explicit degradation mechanisms but also marks the boundary between IRForge's diagnostic benchmark and a deployable restoration/detection architecture. https://arxiv.org/abs/2608.09311
- Pang et al., **Rethinking Evaluation of Infrared Small Target Detection**, 2025 preprint. Argues that aggregate scores hide error modes and cross-dataset robustness. Relevance: motivates row-level error taxonomy and held-out composition evaluation. https://arxiv.org/abs/2509.16888

## Selective prediction

- Geifman and El-Yaniv, **SelectiveNet**, ICML 2019. Formalizes learned reject options and risk–coverage evaluation. IRForge uses post-hoc gates so all methods share the same detector map. https://proceedings.mlr.press/v97/geifman19a.html
- Cattelan and Silva, **How to Fix a Broken Confidence Estimator**, UAI 2024. Shows confidence ranking may remain problematic and evaluates post-hoc selective estimators under shift. Relevance: motivates separating calibration from risk ranking. https://proceedings.mlr.press/v244/cattelan24a.html
- Zhou et al., **A Novel Characterization of Population AURC**, ICML 2025. Provides modern statistical grounding for risk–coverage evaluation. Relevance: motivates reporting AURC alongside one operating point. https://proceedings.mlr.press/v267/zhou25y.html
- Prinster et al., **Conformal Validity Guarantees Exist for Any Data Distribution (and How to Find Them)**, ICML 2024. Shows that guarantees beyond exchangeability require an explicit joint-distribution treatment rather than transferring ordinary conformal calibration unchanged. Relevance: positions H6's held-out drift failure as a stress test, not a contradiction of conformal theory. https://proceedings.mlr.press/v235/prinster24a.html

## Gap used by this artifact

IRForge measures how image-formation changes affect a fixed detector and its rejection rule. The controlled simulator allows matched perturbations and temporal studies, while measured-image generalization remains untested. The [sequence analysis](../artifacts/sequence-pair-analysis/REPORT.md) reports complete paired sequences as the resampling unit and includes both utility and error.

## September 2026 update

[Fu et al., S2CPNet](https://arxiv.org/abs/2604.01934) study cross-domain representations in the frequency domain (April 2026 preprint). Together with RealScene-ISTD and DAISOD, this makes measured cross-dataset testing an essential next step before a detector-generalization claim. The current repository supplies a simulation and analysis tool, with no direct performance comparison against these models.
