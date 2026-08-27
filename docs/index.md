---
layout: home
hero:
  name: ASTRA
  text: Adaptive Spectrum Threat Recognition & Analysis
  tagline: >
    Machine-learning Electronic Support receiver scheduler that decides
    where to listen next — with zero prior intelligence on emitters.
  image:
    src: /astra_logo.svg
    alt: ASTRA Logo
  actions:
    - theme: brand
      text: Get Started
      link: /guide/getting-started
    - theme: alt
      text: Quick Start (3 steps)
      link: /guide/quick-start
    - theme: alt
      text: API Reference
      link: /reference/api

features:
  - icon: 🎯
    title: Adaptive Scheduling
    details: >
      SmartScan learns emitter behaviour on the job: reconnaissance sweep,
      phase-lock pursuit, predict-and-probe, burst characterisation, and
      value-weighted rotation. Intercepts 17 points more threats than
      conventional sweeps.
  - icon: 📊
    title: KPP-Gated Evaluation
    details: >
      Every scheduler is judged against hard Key Performance Parameters
      (threat coverage ≥ 90%, prediction accuracy ≥ 50%, false-alarm rate
      ≤ 5×10⁻⁴). Only SmartScan passes all three gates.
  - icon: 🛰️
    title: Live Sensor Integration
    details: >
      Connect real SDR hardware or radar processors via UDP PDW streams.
      The same scheduler runs online against live data — watch it adapt
      in real time.
  - icon: 🔍
    title: Emitter Identification
    details: >
      Intercepted signal streams are fingerprinted (frequency, pulse width,
      scan rhythm) and matched against the JC Wise-style emitter library
      with confidence scores and threat classification.
  - icon: 🌐
    title: Multi-Receiver Geolocation
    details: >
      K cooperating receivers measure AOA bearings to each emitter.
      Least-squares triangulation estimates positions with CEP accuracy
      analysis.
  - icon: 🤖
    title: Counter-ESM Evasion
    details: >
      Intelligent adversaries that actively evade interception after being
      detected — shifting rotation phases or swapping frequency hop-sets.
      ASTRA must track and predict these agile tactics.
---

<div style="text-align: center; padding: 2rem 0;">
  <p style="font-size: 1.1rem; color: var(--vp-c-text-2);">
    <b>Smart India Hackathon 2026</b> · Defence & Space · Problem ID: SMART SCAN EW
  </p>
  <p style="font-size: 0.9rem; color: var(--vp-c-text-3);">
    7 scheduling policies benchmarked · 200 held-out episodes · 95% confidence intervals
    · p &lt; 1e-4 statistical significance · 57 automated tests
  </p>
</div>
