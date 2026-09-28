import{r as c,j as e,P as k,L as _,S as R,D as P,T as E,c as D}from"./styles-FL_H3Ph3.js";const S=`<p>\uFEFF# ASTRA — Software Documentation</p>
<p><strong>ASTRA — Adaptive Spectrum Threat Recognition &amp; Analysis</strong></p>
<p>Adaptive scan scheduling for Electronic Support receivers.</p>
<p>Version 3.0.0 · SIH 2026 prototype · simulation-based research software, not operational equipment.</p>
<hr />
<h2 id="contents">Contents</h2>
<ol>
<li><a href="#1-introduction">Introduction</a></li>
<li><a href="#2-installation">Installation</a></li>
<li><a href="#3-quick-start">Quick start</a></li>
<li><a href="#4-interface-tour">Interface tour</a></li>
<li><a href="#5-operations-perspective">Operations perspective</a></li>
<li><a href="#6-analysis-perspective">Analysis perspective</a></li>
<li><a href="#7-data--sources-perspective">Data &amp; Sources perspective</a></li>
<li><a href="#8-radar-and-sensor-integration">Radar and sensor integration</a></li>
<li><a href="#9-scenarios">Scenarios</a></li>
<li><a href="#10-datasets-and-calibration">Datasets and calibration</a></li>
<li><a href="#11-scheduling-policies">Scheduling policies</a></li>
<li><a href="#12-evaluation-methodology">Evaluation methodology</a></li>
<li><a href="#13-diagnostics-and-troubleshooting">Diagnostics and troubleshooting</a></li>
<li><a href="#14-testing-without-a-radar">Testing without a radar</a></li>
<li><a href="#15-architecture-reference">Architecture reference</a></li>
<li><a href="#16-local-api-reference">Local API reference</a></li>
<li><a href="#17-command-line-tools">Command-line tools</a></li>
<li><a href="#18-file-formats">File formats</a></li>
<li><a href="#19-frequently-asked-questions">Frequently asked questions</a></li>
<li><a href="#20-glossary">Glossary</a></li>
<li><a href="#21-simulation-fidelity-reference">Simulation fidelity reference</a></li>
</ol>
<hr />
<h2 id="1-introduction">1. Introduction</h2>
<h3 id="1-1-what-astra-is">1.1 What ASTRA is</h3>
<p>ASTRA is a desktop application that schedules the scan pattern of an</p>
<p>Electronic Support (ES) receiver. Such receivers are sensitive but narrowband:</p>
<p>they can listen to only one slice of spectrum at a time while remaining</p>
<p>responsible for a much wider range. Where a conventional receiver sweeps bands</p>
<p>in a fixed pre-mission order, ASTRA decides <strong>where to listen next</strong> based on</p>
<p>what has already been heard — surveying the spectrum, learning each emitter's</p>
<p>behaviour, predicting when periodic emitters will transmit again, and</p>
<p>positioning the receiver on those windows before they open.</p>
<h3 id="1-2-what-problem-it-addresses">1.2 What problem it addresses</h3>
<p>Interception is a two-dimensional search: the receiver must be on the right</p>
<p>frequency at the right time. Fixed scans waste dwell time on empty or</p>
<p>unimportant bands and are slow to return to new or threatening emitters.</p>
<p>Naive adaptivity swings to the opposite failure — camping on one busy band and</p>
<p>missing most threats. ASTRA resolves this tension explicitly, achieving both</p>
<p>high reward and high coverage where reference systems achieve only one.</p>
<h3 id="1-3-what-it-is-not">1.3 What it is not</h3>
<p>ASTRA is a prototype for evaluation. It ships with a physically motivated</p>
<p>simulated RF environment so that it runs anywhere with no hardware; it does not</p>
<p>transmit, jam, or connect to any classified system.</p>
<hr />
<h2 id="2-installation">2. Installation</h2>
<h3 id="2-1-requirements">2.1 Requirements</h3>
<table>
<tr><th>Item</th><th>Requirement</th></tr>
<tr><td>Operating system</td><td>Windows 10/11 (Linux/macOS run from source)</td></tr>
<tr><td>For <code>ASTRA.exe</code></td><td>None beyond the OS; WebView runtime (Edge) ships with Windows</td></tr>
<tr><td>From source</td><td>Python ≥ 3.10 with pip; Node.js ≥ 18 only if rebuilding the UI</td></tr>
</table>
<h3 id="2-2-installer-recommended">2.2 Installer (recommended)</h3>
<ol>
<li>Copy or install the <code>ASTRA</code> folder.</li>
<li>Double-click <strong><code>ASTRA.exe</code></strong>. A console window shows service startup, then</li>
</ol>
<p>the application window opens.</p>
<ol>
<li>Closing the application window does not stop the service by itself; use</li>
</ol>
<p><strong>File → Exit</strong> inside ASTRA, or close the console window.</p>
<h3 id="2-3-from-source">2.3 From source</h3>
<pre><code>git clone &lt;repository> ; cd p1
python -m pip install -r requirements.txt fastapi uvicorn markdown
cd frontend ; npm install ; npm run build ; cd ..
python desktop.py</code></pre>
<h3 id="2-4-browser-only-mode">2.4 Browser-only mode</h3>
<p>Any mode above also works from a normal browser at <code>http://127.0.0.1:&lt;port&gt;</code></p>
<p>(the port is printed at startup). All features are identical; only the window</p>
<p>frame differs.</p>
<hr />
<h2 id="3-quick-start">3. Quick start</h2>
<ol>
<li>Launch ASTRA (Section 2).</li>
<li>Press <strong>Start Mission</strong> on the toolbar (or File → Start paired mission).</li>
<li>Watch the Operations perspective: two receivers fly identical battlefields;</li>
</ol>
<p>blue-grey cells are true transmissions, amber marks intercepts.</p>
<ol>
<li>Open <strong>Tools → Diagnostics</strong> at any time to verify the installation.</li>
<li>Press <strong>User Guide</strong> on the toolbar whenever you need this document.</li>
</ol>
<hr />
<h2 id="4-interface-tour">4. Interface tour</h2>
<p>The main window follows a classic desktop-application layout:</p>
<pre><code>+--------------------------------------------------------------+
| ASTRA   File  View  Run  Tools  Help              ASTRA 1.0.0 |  &lt;- menu bar
+--------------------------------------------------------------+
| [Start Mission] [Stop] | Rate [v] | Diagnostics | User Guide |  &lt;- toolbar
|                                     Home Operations ...      |     + perspectives
+--------------------------------------------------------------+
|                                                              |
|                    workspace (perspective)                   |
|                                                              |
+--------------------------------------------------------------+
| * READY - slot 0/2400      Adaptive Spectrum ...  port 8000  |  &lt;- status bar
+--------------------------------------------------------------+</code></pre>
<h3 id="menu-bar">Menu bar</h3>
<table>
<tr><th>Menu</th><th>Entries</th><th>Purpose</th></tr>
<tr><td>File</td><td>New mission window · Open scenario… · Export results (JSON) · Exit</td><td>Reset the arena, load a battlefield definition, save current benchmarks, shut down</td></tr>
<tr><td>View</td><td>Home · Operations · Analysis · Data &amp; Sources · Full screen</td><td>Perspective switching</td></tr>
<tr><td>Run</td><td>Start / Stop paired mission · Rate presets</td><td>Mission control and simulation rate</td></tr>
<tr><td>Tools</td><td>Diagnostics… · Open data folder</td><td>Self-test of the installation</td></tr>
<tr><td>Help</td><td>User guide · About ASTRA</td><td>This document; version information</td></tr>
</table>
<h3 id="toolbar">Toolbar</h3>
<p>Run controls (start/stop), simulation-rate selector, quick access to</p>
<p>Diagnostics and this guide, and the perspective switcher on the right.</p>
<h3 id="status-bar">Status bar</h3>
<p>Live state: <code>READY</code> or <code>RUNNING - slot n/T</code>, the product name, the local port,</p>
<p>and a link to the user guide.</p>
<hr />
<h2 id="5-operations-perspective">5. Operations perspective</h2>
<p>Two panels fly simultaneously:</p>
<ul>
<li><strong>Receiver A — SmartScan (adaptive).</strong> Surveys the spectrum, estimates emitter</li>
</ul>
<p>rhythms, predicts transmission windows and arrives before they open.</p>
<ul>
<li><strong>Receiver B — sequential sweep (conventional).</strong> Visits every band in fixed</li>
</ul>
<p>order, ignoring content — standard practice without intelligence.</p>
<p>Both receivers experience <strong>byte-identical battlefields</strong> (same emitters, same</p>
<p>noise draws), so any difference in outcome is attributable to scanning strategy</p>
<p>alone.</p>
<p>Waterfall reading:</p>
<table>
<tr><th>Symbol</th><th>Meaning</th></tr>
<tr><td>Blue-grey cell</td><td>An emitter truly transmitted on that band in that slot (ground truth)</td></tr>
<tr><td>Bright vertical band</td><td>The band that receiver is currently tuned to</td></tr>
<tr><td>Amber marker</td><td>Confirmed intercept (receiver tuned to a transmitting band)</td></tr>
</table>
<p>Per-receiver counters beneath each waterfall update continuously: threat</p>
<p>coverage, threats intercepted (of total present), reward per dwell, hit rate,</p>
<p>false alarms. When an episode completes a result line summarises the A/B</p>
<p>outcome, and the next episode begins automatically on a fresh scenario.</p>
<p>Controls: toolbar <strong>Rate</strong> selects simulation speed (slots per second); rate</p>
<p>affects wall-clock pacing only, never outcomes. <strong>File → Open scenario…</strong></p>
<p>starts a mission on a stored battlefield definition.</p>
<hr />
<h2 id="6-analysis-perspective">6. Analysis perspective</h2>
<p>All values are generated by the bundled experiment suite from stored scenario</p>
<p>seeds; nothing is hand-entered.</p>
<p><strong>KPP gate table.</strong> Each scheduler is first judged against hard Key Performance</p>
<p>Parameters (threat coverage ≥ 0.90, prediction accuracy ≥ 0.50, false-alarm</p>
<p>rate ≤ 5×10⁻⁴ per slot). Only systems passing every KPP are considered</p>
<p>mission-capable and ranked by the Mission Effectiveness Score (MES).</p>
<p><strong>Monte Carlo table.</strong> Mean ± 95% confidence intervals across 50 held-out (canonical protocol: 24 bands × 3000 slots, base_seed 9000)</p>
<p>episodes for reward, threat coverage, prediction accuracy, intercept rate,</p>
<p>false-alarm rate, time-to-first-intercept and intercept-time prediction error.</p>
<p>Paired permutation tests on the gated score separate SmartScan from every</p>
<p>reference policy (p &lt; 1e-4, Holm-Bonferroni corrected).</p>
<p><strong>Evidence gallery.</strong> Generated figures: effectiveness under the gate,</p>
<p>scheduler comparison, training vs held-out greedy evaluation curves, ablation</p>
<p>study, ROC across sensitivity thresholds, geolocation accuracy versus receiver</p>
<p>count.</p>
<p>File → Export results (JSON) writes the full machine-readable payload behind</p>
<p>these tables to disk.</p>
<hr />
<h2 id="7-data-sources-perspective">7. Data &amp; Sources perspective</h2>
<p>Three panels manage inputs and artefacts.</p>
<h3 id="sensor-sources">Sensor sources</h3>
<p>Attach live pulse-descriptor-word (PDW) feeds; each attached source reports its</p>
<p>cumulative PDW count and instantaneous rate, proving connectivity before real</p>
<p>hardware is wired in.</p>
<table>
<tr><th>Type</th><th>Parameters</th><th>Typical use</th></tr>
<tr><td>UDP feed</td><td>port (1024–65535), bind address</td><td>SDR sweeps, radar processors, <code>tools/pdw_generator.py</code>, <code>tools/sdr_bridge.py</code></td></tr>
<tr><td>Log file tail</td><td>path to growing JSONL/CSV</td><td>Third-party equipment writing PDW logs</td></tr>
<tr><td>Internal simulated scene</td><td>band count, seed</td><td>Testing with no hardware at all</td></tr>
</table>
<p>Detach removes the source cleanly. Errors (for example a busy UDP port or a</p>
<p>missing file) are shown inline on the source row.</p>
<h3 id="scenario-library">Scenario library</h3>
<p>Every JSON scenario in <code>/scenarios</code> with its band count and horizon. **Fly</p>
<p>paired** starts a new paired mission using that battlefield definition.</p>
<h3 id="trained-models">Trained models</h3>
<p>Model artifacts (<code>/models/*.npz</code>) with their policy class, band count and an</p>
<p>integrity verdict. Artifacts are pickle-free NumPy archives validated on load;</p>
<p>a corrupt file is flagged here rather than executed.</p>
<hr />
<h2 id="8-radar-and-sensor-integration">8. Radar and sensor integration</h2>
<h3 id="8-1-integration-contract">8.1 Integration contract</h3>
<p>ASTRA consumes standard ESM measurements — <strong>pulse descriptor words</strong>:</p>
<pre><code>{"toa_us": 1000.0, "freq_mhz": 9450.0, "pw_us": 1.5, "pa_db": 12.0, "aoa_deg": 90.0}</code></pre>
<table>
<tr><th>Field</th><th>Meaning</th><th>Required</th></tr>
<tr><td><code>toa_us</code></td><td>time of arrival, microseconds</td><td>yes</td></tr>
<tr><td><code>freq_mhz</code></td><td>centre frequency, MHz</td><td>yes</td></tr>
<tr><td><code>pw_us</code></td><td>pulse width, µs</td><td>optional (default 1.0)</td></tr>
<tr><td><code>pa_db</code></td><td>amplitude, dB</td><td>optional</td></tr>
<tr><td><code>aoa_deg</code></td><td>angle of arrival, degrees</td><td>optional</td></tr>
</table>
<p>Datagrams may carry <strong>one JSON object or a JSON array</strong> of objects. A single</p>
<p>datagram per pulse-group per slot is the intended cadence (default slot =</p>
<p>1 ms), but the pipeline tolerates bursty delivery and re-bins by <code>toa_us</code>.</p>
<h3 id="8-2-wiring-any-radar-sdr-processor">8.2 Wiring any radar / SDR processor</h3>
<p>Three supported paths, in increasing fidelity:</p>
<ol>
<li><strong>Synthetic generator (no hardware).</strong></li>
</ol>
<p><code>python tools/pdw_generator.py --port 5555 --rate 400</code></p>
<p>emits realistic multi-emitter traffic over UDP for integration testing.</p>
<ol>
<li><strong>Bridge an existing sweep log.</strong></li>
</ol>
<p><code>python tools/sdr_bridge.py --mode csv --csv sweep.csv --out-port 5555</code></p>
<p>converts CSV sweeps (or relays an existing JSON feed with <code>--mode udp</code>) into</p>
<p>the ASTRA datagram format.</p>
<ol>
<li><strong>Direct emission.</strong> Your processor writes the JSON schema above straight to</li>
</ol>
<p>ASTRA's UDP port (attach the source in <strong>Data &amp; Sources</strong>, then select the</p>
<p>same port).</p>
<h3 id="8-3-adapting-exotic-front-ends">8.3 Adapting exotic front-ends</h3>
<p>If your equipment produces another format, write a ~30-line adapter that maps</p>
<p>it onto the five-field PDW schema and forwards datagrams — see</p>
<p><code>tools/sdr_bridge.py</code> as the template. Channelised or FFT-based receivers can</p>
<p>emit one PDW per detected peak per dwell.</p>
<h3 id="8-4-notes-and-limits">8.4 Notes and limits</h3>
<ul>
<li>Frequency-to-band mapping uses the scenario's <code>[fmin, fmax]</code>; out-of-range</li>
</ul>
<p>frequencies clamp to the edge bands.</p>
<ul>
<li>The demo pipeline assumes a single receiver location; AOA is carried end to</li>
</ul>
<p>end for identification and geolocation studies.</p>
<ul>
<li>No data leaves the machine: all networking is local loopback unless you bind</li>
</ul>
<p>otherwise deliberately.</p>
<hr />
<h2 id="9-scenarios">9. Scenarios</h2>
<p>A scenario is a JSON file in <code>/scenarios</code>. Key fields (all optional):</p>
<table>
<tr><th>Field</th><th>Default</th><th>Meaning</th></tr>
<tr><td><code>n_bands</code></td><td>24</td><td>number of frequency bins</td></tr>
<tr><td><code>T</code></td><td>3000</td><td>episode length in slots</td></tr>
<tr><td><code>seed</code></td><td>0</td><td>reproducibility seed</td></tr>
<tr><td><code>n_stationary</code> / <code>n_agile</code> / <code>n_periodic</code> / <code>n_spatial</code> / <code>n_clutter</code></td><td>6/4/4/3/8</td><td>emitter mix</td></tr>
<tr><td><code>snr_mean_db</code>, <code>snr_std_db</code></td><td>12 / 4</td><td>signal strength distribution</td></tr>
<tr><td><code>freq_min_mhz</code>, <code>freq_max_mhz</code></td><td>2000–18000</td><td>tuning range</td></tr>
<tr><td><code>period_range</code>, <code>on_len_range</code>, <code>dwell_range</code>, <code>hop_set_range</code></td><td>class priors</td><td>behavioural ranges</td></tr>
</table>
<p>Scenario + seed ⇒ exactly reproducible battlefield.</p>
<hr />
<h2 id="10-datasets-and-calibration">10. Datasets and calibration</h2>
<p>ASTRA honours the referenced datasets:</p>
<ul>
<li><strong>JC Wise, Radar Emitter Database (2024)</strong> — basis of the identification</li>
</ul>
<p>library profiles used to tag intercepted streams.</p>
<ul>
<li><strong>Alan Turing Institute synthetic radar dataset (HuggingFace)</strong> — imported by</li>
</ul>
<p>Dataset Studio (Streamlit dashboard) online when reachable, with a</p>
<p>schema-identical offline fallback so everything works air-gapped.</p>
<p>Imported PDWs drive scenario calibration: observed frequency clusters become</p>
<p>emitters, and their temporal statistics set behavioural classes.</p>
<hr />
<h2 id="11-scheduling-policies">11. Scheduling policies</h2>
<p>Seven policies ship with the system; six exist as honest references:</p>
<table>
<tr><th>Name</th><th>Class</th><th>Character</th></tr>
<tr><td>Sequential sweep</td><td>open loop</td><td>fixed cyclic visitation</td></tr>
<tr><td>Random scan</td><td>open loop</td><td>uniform random selection</td></tr>
<tr><td>Priority sweep</td><td>open loop</td><td>prior-intelligence ordering</td></tr>
<tr><td>UCB bandit</td><td>adaptive, exploit-only</td><td>converges on richest band (demonstrates the exploit trap)</td></tr>
<tr><td>Linear Q-learning</td><td>reinforcement learning</td><td>learned value over hand-crafted features</td></tr>
<tr><td>Deep Q-network</td><td>deep RL</td><td>MLP + replay + target network</td></tr>
<tr><td><strong>SmartScan</strong></td><td>proposed hybrid</td><td>five behaviours multiplexed by learned confidence</td></tr>
</table>
<p>SmartScan's behaviours: reconnaissance sweep; cued pursuit of validated phase</p>
<p>locks; predict-and-probe of candidate rhythms; characterisation bursts;</p>
<p>value-weighted rotation with recency guarantees and an exploitation ramp.</p>
<p>Locks require repeated mutually isolated detections on one SNR+AOA fingerprint</p>
<p>and are deleted automatically after repeated failed predictions.</p>
<hr />
<h2 id="12-evaluation-methodology">12. Evaluation methodology</h2>
<p>Following defence test &amp; evaluation practice:</p>
<ol>
<li><strong>KPPs (hard gates).</strong> Threat coverage ≥ 0.90 · prediction accuracy ≥ 0.50 ·</li>
</ol>
<p>false alarms ≤ 5×10⁻⁴/slot. Failing any gate ⇒ <em>not mission-capable</em>.</p>
<ol>
<li><strong>MES ranking.</strong> Among capable systems, mean of six normalised</li>
</ol>
<p>problem-statement figures of merit (Pd, Pfa performance, intercept rate,</p>
<p>reward, prediction accuracy, intercept-time error).</p>
<ol>
<li><strong>Statistics.</strong> Paired per-episode permutation tests on the gated score with</li>
</ol>
<p>Holm-Bonferroni correction; 50 held-out episodes; 95% confidence intervals.</p>
<p>Headline outcome: **SmartScan is the only mission-capable scheduler in the</p>
<p>field** and leads every comparator at p &lt; 1e-4 on gated MES. Learning claims</p>
<p>are backed by held-out greedy evaluation; the deep-network reference's decline</p>
<p>on this sparse task is reported as measured.</p>
<p>Regenerate everything:</p>
<pre><code>python -m ewsmart.experiments --suite full</code></pre>
<hr />
<h2 id="13-diagnostics-and-troubleshooting">13. Diagnostics and troubleshooting</h2>
<p><strong>Tools → Diagnostics</strong> verifies the installation: module imports, environment</p>
<p>boot, benchmark presence, figure inventory, model-artifact integrity, frontend</p>
<p>bundle, manual availability and a UDP loopback test.</p>
<table>
<tr><th>Symptom</th><th>Likely cause</th><th>Remedy</th></tr>
<tr><td>Window opens blank</td><td>frontend bundle missing</td><td>rebuild: <code>cd frontend &amp;&amp; npm run build</code></td></tr>
<tr><td>"Benchmark data: not generated" on Home</td><td>suite never ran</td><td>run the experiment suite command above</td></tr>
<tr><td>Source row shows <code>WinError 10048</code></td><td>UDP port already bound</td><td>choose another port; stop the other process</td></tr>
<tr><td>Source attaches but 0 PDWs</td><td>no sender / wrong port / firewall</td><td>start <code>tools/pdw_generator.py --port &lt;same&gt;</code>; allow python through the firewall</td></tr>
<tr><td>Analysis empty after export</td><td>results file absent</td><td>regenerate via experiment suite</td></tr>
<tr><td>Exit did nothing</td><td>popup blocked for <code>window.close()</code></td><td>close the console window; service stops with it</td></tr>
</table>
<hr />
<h2 id="14-testing-without-a-radar">14. Testing without a radar</h2>
<p>Full instructions in <a href="../HOW_TO_TEST.md"><code>HOW_TO_TEST.md</code></a>. Summary ladder:</p>
<ol>
<li><strong>Automated tests</strong> — 50 backend + 7 interface tests, each runnable standalone.</li>
<li><strong>In-app diagnostics</strong> — Tools → Diagnostics.</li>
<li><strong>Internal simulated scene source</strong> — attach in Data &amp; Sources; counts PDWs with zero hardware.</li>
<li><strong>UDP generator</strong> — <code>tools/pdw_generator.py</code> streams realistic emitter traffic to a chosen port.</li>
<li><strong>CSV replay bridge</strong> — <code>tools/sdr_bridge.py</code> replays recorded sweeps.</li>
<li><strong>Paired missions</strong> — statistical A/B evidence at any simulation rate.</li>
</ol>
<p>Recommended edge cases: malformed datagrams (ignored gracefully), burst floods,</p>
<p>empty feeds (source stays healthy, zero counts), port conflicts (inline error),</p>
<p>scenario extremes (few bands, short horizons), repeated start/stop cycling, two</p>
<p>browser windows sharing one service.</p>
<hr />
<h2 id="15-architecture-reference">15. Architecture reference</h2>
<pre><code>desktop.py            app-window launcher: free port, uvicorn thread, Edge/Chrome --app window
server/api.py         FastAPI: results, figures, scenarios, models, sources, diagnostics,
                      SSE live arena, manual renderer, shutdown hook
server/livesim.py     paired A/B simulation thread emitting synchronised frames
server/sources.py     sensor source hub: udp / file / sim with health + rates
ewsmart/environment   RF scene: four emitter classes; occupancy truth matrix
ewsmart/receiver      narrowband detection physics; AOA; PDWs
ewsmart/schedulers    seven policies incl. SmartScan
ewsmart/periodic      Rayleigh period estimation + integer refinement
ewsmart/metrics       figures of merit; KPP gate; Mission Effectiveness Score
ewsmart/experiments   Monte Carlo, significance, ROC, sensitivity, ablation, geolocation
ewsmart/live          streaming ingestion core (simulated / UDP / file tail)
frontend/             React application (menu bar, toolbar, perspectives, status bar)
tools/                sdr_bridge.py, pdw_generator.py, build_exe.ps1
docs/                 this document</code></pre>
<hr />
<h2 id="16-local-api-reference">16. Local API reference</h2>
<p>All endpoints are local-first (<code>127.0.0.1</code>). Interactive OpenAPI UI: <code>/api-docs</code>.</p>
<table>
<tr><th>Method &amp; path</th><th>Purpose</th></tr>
<tr><td>GET <code>/api/meta</code></td><td>name, version, availability flags</td></tr>
<tr><td>GET <code>/api/health</code></td><td>liveness probe</td></tr>
<tr><td>GET <code>/api/summary</code></td><td>full benchmark payload</td></tr>
<tr><td>GET <code>/api/figures</code> · <code>/api/figures/{name}.png</code></td><td>figure inventory and images</td></tr>
<tr><td>GET <code>/api/scenarios</code></td><td>scenario library</td></tr>
<tr><td>POST <code>/api/live/start?speed&amp;scenario</code></td><td>start paired mission (optionally from a named scenario)</td></tr>
<tr><td>POST <code>/api/live/stop</code></td><td>stop mission</td></tr>
<tr><td>GET <code>/api/live/status</code></td><td>running flag, slot, per-scheduler KPIs</td></tr>
<tr><td>GET <code>/api/live/stream</code></td><td>SSE frame stream</td></tr>
<tr><td>GET/POST/DELETE <code>/api/sources</code></td><td>sensor source management</td></tr>
<tr><td>GET <code>/api/models</code></td><td>model artifacts + integrity</td></tr>
<tr><td>GET <code>/api/diagnostics</code></td><td>self-test checklist</td></tr>
<tr><td>GET <code>/manual</code></td><td>rendered user guide</td></tr>
<tr><td>POST <code>/api/shutdown</code></td><td>graceful shutdown (used by File → Exit)</td></tr>
</table>
<hr />
<h2 id="17-command-line-tools">17. Command-line tools</h2>
<table>
<tr><th>Command</th><th>Purpose</th></tr>
<tr><td><code>python desktop.py</code></td><td>launch the desktop application</td></tr>
<tr><td><code>python -m ewsmart.runner --scenario scenarios/demo.json --save-dir models --json-out results.json</code></td><td>train + evaluate one scenario</td></tr>
<tr><td><code>python -m ewsmart.experiments --suite full</code></td><td>regenerate all published results</td></tr>
<tr><td><code>python tools/pdw_generator.py --port 5555 --rate 400</code></td><td>synthetic PDW feed over UDP</td></tr>
<tr><td><code>python tools/sdr_bridge.py --mode csv --csv sweep.csv --out-port 5555</code></td><td>bridge CSV/JSON sweeps into ASTRA format</td></tr>
<tr><td><code>powershell -File tools/build_exe.ps1</code></td><td>build <code>dist/ASTRA/ASTRA.exe</code></td></tr>
</table>
<hr />
<h2 id="18-file-formats">18. File formats</h2>
<p><strong>Scenario JSON</strong> — fields per Section 9.</p>
<p><strong>PDW datagram</strong> — Section 8.1.</p>
<p><strong>Model artifact (.npz)</strong> — <code>meta</code> = JSON string \`{format:"ewsmart-npz-v1",</p>
<p>class, n_bands, ...}<code> plus plain arrays; loaded with </code>allow_pickle=False\`.</p>
<p><strong>results/suite_results.json</strong> — sections: <code>monte_carlo</code>, <code>significance</code>,</p>
<p><code>mission_effectiveness</code>, <code>significance_gated_mes</code>, <code>learning</code>,</p>
<p><code>identification</code>, <code>roc</code>, <code>sensitivity</code>, <code>ablation</code>, <code>multireceiver</code>,</p>
<p><code>geolocation</code>.</p>
<hr />
<h2 id="19-frequently-asked-questions">19. Frequently asked questions</h2>
<p><strong>Does closing the app window stop the service?</strong> Use File → Exit for a clean</p>
<p>shutdown; the console window also stops the service when closed.</p>
<p><strong>Can several windows share one service?</strong> Yes — open additional browser tabs</p>
<p>to the printed URL; all views stay in sync because state lives server-side.</p>
<p><strong>Where do numbers come from?</strong> Experiments over stored seeds; re-run the suite</p>
<p>to reproduce byte-for-byte.</p>
<p><strong>Is any data sent to the internet?</strong> No. Networking is loopback except an</p>
<p>optional HuggingFace fetch inside Dataset Studio, which falls back offline.</p>
<p><strong>Why does Receiver B exist?</strong> Controlled comparison. Identical battlefields</p>
<p>make the strategy the only variable.</p>
<hr />
<h2 id="20-glossary">20. Glossary</h2>
<table>
<tr><th>Term</th><th>Meaning</th></tr>
<tr><td>ES / ESM</td><td>Electronic Support — passive search, intercept, analysis of emissions</td></tr>
<tr><td>PDW</td><td>Pulse Descriptor Word (TOA, frequency, width, amplitude, AOA)</td></tr>
<tr><td>Dwell</td><td>One listening interval on one band</td></tr>
<tr><td>Slot</td><td>Discrete time step of the simulation (default 1 ms)</td></tr>
<tr><td>Phase lock (ASTRA)</td><td>Validated estimate of a periodic emitter's period and window timing</td></tr>
<tr><td>KPP</td><td>Key Performance Parameter — hard pass/fail requirement</td></tr>
<tr><td>MES</td><td>Mission Effectiveness Score — composite FoM after gating</td></tr>
<tr><td>CEP</td><td>Circular Error Probable — median geolocation error radius</td></tr>
</table>
<hr />
<h2 id="21-simulation-fidelity-reference">21. Simulation fidelity reference</h2>
<p>ASTRA's scheduler works on a discrete band/time grid because scheduling is what</p>
<p>it studies. This chapter documents the <em>physical</em> layers underneath that grid:</p>
<p>pulse-level signal processing, waveform classes, front-end impairments, the</p>
<p>angle-of-arrival measurement, and the two deployment artifacts (scenario</p>
<p>auto-calibration and the fixed-point kernel). Each module states what it does,</p>
<p>how it works, and which measured number demonstrates it.</p>
<h3 id="21-1-pulse-level-deinterleaving-ewsmart-deinterleave-py">21.1 Pulse-level deinterleaving (<code>ewsmart/deinterleave.py</code>)</h3>
<p><strong>What it does.</strong> A real ES receiver's wideband front-end receives an</p>
<p>interleaved stream of pulses from every emitter in view — at combat densities</p>
<p>10^5–10^6 pulses/second — and must separate that stream back into individual</p>
<p>emitters before anything can be tracked or identified. ASTRA performs that</p>
<p>separation instead of assuming it away.</p>
<p><strong>How it works.</strong> Four classical stages:</p>
<ol>
<li><code>emit_pulse_train</code> synthesises one emitter's pulses in a dwell (TOA, RF,</li>
</ol>
<p>pulse width, amplitude, AOA) from its PRI model.</p>
<ol>
<li><code>interleave</code> builds the raw, time-ordered PDW stream a receiver would see.</li>
<li><code>deinterleave</code> separates it: descriptor clustering on (RF, PW, AOA), then an</li>
</ol>
<p>all-pairs difference-of-time-of-arrival histogram to find the dominant PRI,</p>
<p>then coarse-to-fine period sharpening by *phase-histogram entropy</p>
<p>minimisation*, then a circular-phase test that discriminates</p>
<p>fixed / staggered / jittered / aperiodic trains.</p>
<ol>
<li><code>deinterleave_accuracy</code> scores the result against ground truth.</li>
</ol>
<p>Two details matter physically: amplitude is derived with the peak-to-average</p>
<p>term (<code>pri/pw</code>) that makes a low-duty pulsed radar detectable at a lower</p>
<p>average power, and a staggered train's reported PRI is the <em>mean interval</em></p>
<p>(frame/k) — the quantity a real PRI estimator reports.</p>
<p><strong>Measured.</strong> Four emitters (fixed 250 µs, staggered 3-level 97 µs, jittered</p>
<p>410 µs ±12%, LPI 600 µs) interleaved into one stream: fragmentation 1.0, pulse</p>
<p>purity 1.0, attributed fraction 1.0, mean PRI error 0.4%, PRI-model</p>
<p>classification 100%. The deinterleaver never reads the ground-truth label</p>
<p>(leakage asserted by test).</p>
<h3 id="21-2-waveform-classes-and-the-matched-filter">21.2 Waveform classes and the matched filter</h3>
<p><strong>What it does.</strong> Models Low Probability of Intercept radar: an emitter may</p>
<p>spread its energy over a large time-bandwidth product so that it sits <em>below</em></p>
<p>the noise floor in any one channel.</p>
<p><strong>How it works.</strong> <code>EmitterSpec.waveform</code> is <code>pulsed</code>, <code>lpi_fmcw</code> or</p>
<p><code>lpi_barker</code> with a time-bandwidth product <code>tb_product</code>. An LPI emitter's</p>
<p>in-channel SNR is reduced by exactly <code>10 log10(BT)</code>; a receiver running the</p>
<p>matched-filter / de-chirp bank (<code>matched_filter: true</code>, on by default) earns</p>
<p>that gain back before the detection decision.</p>
<p><strong>Measured.</strong> A −14 dB in-channel LPI emitter with BT = 256 (24.1 dB gain):</p>
<p>283 of 300 dwells detected with the matched filter, 5 of 300 without. The</p>
<p>switch is in the scenario config, so the comparison is reproducible.</p>
<h3 id="21-3-rf-front-end-impairments-ewsmart-frontend-py">21.3 RF front-end impairments (<code>ewsmart/frontend.py</code>)</h3>
<p><strong>What it does.</strong> Models the hardware between the antenna and the digitiser so</p>
<p>its costs are measurable rather than narrated.</p>
<table>
<tr><th>Effect</th><th>Model</th></tr>
<tr><td>Retune settling</td><td><code>settling_time_us</code> of each retuned dwell is blanked (integration time, hence processing gain, is lost)</td></tr>
<tr><td>LNA blocking</td><td>above the 1 dB compression point the noise floor rises (compression + LO phase-noise reciprocal mixing)</td></tr>
<tr><td>Mixer non-linearity</td><td>third-order products 2f1−f2 / 2f2−f1 at level <code>3<em>P_tone − 2</em>IP3</code>; image and <code>m<em>f_RF ± n</em>f_LO</code> spur responses enumerated</td></tr>
<tr><td>ADC</td><td>12-bit full-scale saturation with odd-harmonic fold-back bounded by the spurious-free dynamic range</td></tr>
</table>
<p><strong>How to use it.</strong> <code>ESReceiver.attach_front_end(FrontEnd(FrontEndSpec(...)))</code>.</p>
<p>Below P1dB the model is <em>exactly</em> linear (zero noise rise), so attaching a</p>
<p>front-end never silently changes normal operation; the impairment appears only</p>
<p>where physics says it should.</p>
<h3 id="21-4-angle-of-arrival-measurement-ewsmart-aoa-py">21.4 Angle-of-arrival measurement (<code>ewsmart/aoa.py</code>)</h3>
<p><strong>What it does.</strong> Replaces the constant 2.5 degree Gaussian bearing error with a</p>
<p>dual-baseline phase interferometer whose error is coupled to SNR and frequency</p>
<p>through the Cramer-Rao bound.</p>
<p><strong>How it works.</strong> The coarse (5 cm) baseline measures the angle unambiguously</p>
<p>across the field of view; the fine (20 cm) baseline is four times more precise</p>
<p>but wraps, so its ambiguity is resolved against the coarse estimate, with exact</p>
<p>hypothesis ties broken by angular proximity, as real systems do. A</p>
<p>front/back-ambiguous single array face is modelled honestly: the folded bearing</p>
<p>is restored using the observation hemisphere, standing in for the second array</p>
<p>face. <code>aoa_model: "monopulse"</code> or <code>"fixed"</code> select the alternative models.</p>
<p><strong>Measured.</strong> At 20 dB SNR the error is 0.35-0.5 degrees and unbiased across all</p>
<p>eight compass bearings; at -10 dB it degrades to tens of degrees</p>
<p>(CRLB-consistent). That coupling is the point: weak or high-frequency emitters</p>
<p>fingerprint poorly, which the scheduler experiences as stream fragmentation.</p>
<h3 id="21-5-scenario-auto-calibration-ewsmart-calibration-py">21.5 Scenario auto-calibration (<code>ewsmart/calibration.py</code>)</h3>
<p><strong>What it does.</strong> Derives the scheduler's behaviour constants from the scenario</p>
<p>scale instead of hard-coding values tuned for 24 bands x 3000 slots.</p>
<p><strong>How it works.</strong> <code>calibrate(n_bands, T, n_emitters)</code> returns <code>recon_factor</code>,</p>
<p><code>burst_horizon</code>, <code>stale_revisit_factor</code>, <code>pursuit_budget</code>, <code>pursuit_window</code>,</p>
<p><code>hop_min_obs</code>, <code>lock_hits</code> and <code>exploit_ramp</code>, each from a documented formula</p>
<p>over the band, time and density scales. On the canonical scenario it reproduces</p>
<p>the shipped constants exactly, so calibration is a no-op where the tuning is</p>
<p>known good and adapts elsewhere: an 8-band radio survey or a 128-band full</p>
<p>ELINT sweep both get appropriately sized behaviour.</p>
<h3 id="21-6-fixed-point-real-time-kernel-ewsmart-realtime-py">21.6 Fixed-point real-time kernel (<code>ewsmart/realtime.py</code>)</h3>
<p><strong>What it does.</strong> Provides the per-slot decision in Q8.8 integer arithmetic as</p>
<p>the concrete port artifact for FPGA/DSP deployment.</p>
<p><strong>How it works.</strong> Every statistic is quantised once on write with saturation;</p>
<p>the per-slot score is an integer multiply-accumulate over <code>n_bands</code> lanes</p>
<p>(O(n_bands), no dynamic allocation, no per-slot transcendental); the log/sqrt</p>
<p>terms are cached and recomputed only when the underlying statistics change.</p>
<p><code>tools/export_cpp_kernel.py</code> emits the same arithmetic as a header-only C++</p>
<p>kernel (<code>build/rtl/astra_policy_kernel.hpp</code>) plus a <code>kernel_metadata.json</code></p>
<p>complexity contract.</p>
<p><strong>Measured.</strong> Over 200 randomised states the fixed-point argmax matches the</p>
<p>float reference, and the recorded decision cost remains under the 1 ms gate.</p>
<h3 id="21-7-learned-behaviour-arbitration-ewsmart-meta-py">21.7 Learned behaviour arbitration (<code>ewsmart/meta.py</code>)</h3>
<p><strong>What it does.</strong> Adds a genuine learning component to the <em>decision core</em>: a</p>
<p>linear-upper-confidence-bound contextual bandit that learns which behaviour</p>
<p>(survey, pursue, probe, camp, rotate) pays in which situation, from hits and</p>
<p>misses alone.</p>
<p><strong>How it works.</strong> The scheduler tags every decision with the behaviour that</p>
<p>produced it and, on the dwell result, folds <code>(context, behaviour, reward)</code> into</p>
<p>the arbiter. A safe action mask means the arbiter can only choose among</p>
<p>behaviours whose preconditions hold, so an immature model cannot destabilise a</p>
<p>proven policy; its learned preferences are inspectable via <code>arbiter.score()</code>.</p>
<p>Cross-episode persistence is available through <code>get_state</code> / <code>set_state</code>.</p>
<p><strong>Measured.</strong> A full episode trains the arbiter from 500+ outcome triples, and</p>
<p>in a two-armed test it converges to preferring the rewarded behaviour.</p>
<h3 id="21-8-documentation-pipeline">21.8 Documentation pipeline</h3>
<p><code>tools/export_docs.py</code> makes this manual the single source of truth: it</p>
<p>converts the markdown to HTML for the website's Documentation page</p>
<p>(<code>website/src/content/docsHtml.ts</code>), copies it to</p>
<p><code>website/public/docs/manual.md</code> for the "Download (.md)" button, and emits the</p>
<p>section index the site's table of contents is built from. The desktop</p>
<p>application serves the same file at <code>/manual</code>; nothing is maintained twice.</p>`;function N(t){const o=[],n=/<h2[^>]*\bid="([^"]+)"[^>]*>([\s\S]*?)<\/h2>/g;let s;for(;(s=n.exec(t))!==null;){const l=s[1];if(l==="contents")continue;const p=s[2].replace(/<[^>]*>/g,"").replace(/&amp;/g,"&").trim(),h=(p.match(/^(\d+)\./)??[])[1]??"",m=p.replace(/^\d+\.\s*/,"");o.push({id:l,num:h,title:m})}return o}function x(t,o){const n=t.indexOf("<h2",o+4),s=n===-1?t.length:n;return t.slice(o,s).replace(/<hr\s*\/?>/g,"").trim()}function O(t,o){const n=t.indexOf(`<h2 id="${o}"`);if(n===-1){const s=t.indexOf(`id="${o}"`);if(s===-1)return"<p>Section not found — regenerate docs with <code>python -m tools.export_docs</code>.</p>";const l=t.lastIndexOf("<h2",s);return x(t,l===-1?s:l)}return x(t,n)}function j(){const t=c.useMemo(()=>N(S),[]),[o,n]=c.useState(0),[s,l]=c.useState(""),[p,h]=c.useState(!1),m=c.useRef(null),b=c.useMemo(()=>{const r=s.trim().toLowerCase();return r?t.map((a,i)=>({s:a,i})).filter(({s:a})=>a.title.toLowerCase().includes(r)||a.num.includes(r)):t.map((a,i)=>({s:a,i}))},[t,s]);c.useEffect(()=>{const r=decodeURIComponent(window.location.hash.replace(/^#/,""));if(!r)return;const a=t.findIndex(i=>i.id===r);a>=0&&n(a)},[t]),c.useEffect(()=>{window.scrollTo(0,0);const r=t[o];r&&(history.replaceState(null,"","#"+r.id),document.title=`${r.num?r.num+". ":""}${r.title} — ASTRA Docs`);const a=m.current;a&&a.querySelectorAll("pre").forEach(i=>{if(i.querySelector(".code-copy"))return;const d=document.createElement("button");d.className="code-copy",d.type="button",d.textContent="copy",d.addEventListener("click",()=>{var w,v;const T=((w=i.querySelector("code"))==null?void 0:w.textContent)??i.textContent??"";(v=navigator.clipboard)==null||v.writeText(T).then(()=>{d.textContent="copied ✓",setTimeout(()=>d.textContent="copy",1400)}).catch(()=>d.textContent="Ctrl+C")}),i.appendChild(d)})},[o,t]),c.useEffect(()=>{const r=a=>{var d;const i=(d=a.target)==null?void 0:d.tagName;i==="INPUT"||i==="TEXTAREA"||(a.key==="ArrowRight"&&o<t.length-1&&n(o+1),a.key==="ArrowLeft"&&o>0&&n(o-1))};return window.addEventListener("keydown",r),()=>window.removeEventListener("keydown",r)},[o,t.length]);const y=t[o],A=y?O(S,y.id):"",u=t[o-1],g=t[o+1],f=r=>{n(r),h(!1)};return e.jsxs("div",{className:"docs-page",children:[e.jsx(k,{}),e.jsx("header",{className:"doc-topbar",children:e.jsxs("div",{className:"doc-topbar-inner",children:[e.jsx("a",{href:"/","aria-label":"ASTRA home",children:e.jsx(_,{size:24})}),e.jsx("a",{href:"/",className:"brand-txt",children:"ASTRA"}),e.jsxs("span",{className:"crumb",children:["/ ",e.jsx("b",{children:"Documentation"})]}),e.jsx("span",{className:"doc-ver",children:R}),e.jsxs("div",{className:"doc-actions",children:[e.jsx("button",{className:"doc-mobile-toc",type:"button",onClick:()=>h(!p),children:"☰ Contents"}),e.jsx("a",{className:"btn ghost",href:"/docs/manual.md",download:!0,children:"Download .md"}),e.jsx("a",{className:"btn ghost",href:P,download:!0,children:"Get the app"}),e.jsx(E,{}),e.jsx("a",{className:"btn primary",href:"/",children:"Back to site"})]})]})}),e.jsxs("div",{className:"doc-body",children:[e.jsxs("aside",{className:"doc-sidebar"+(p?" open":""),children:[e.jsx("h3",{children:"Table of Contents"}),e.jsx("div",{className:"dsearch",children:e.jsx("input",{type:"search",placeholder:"Filter sections…",value:s,onChange:r=>l(r.target.value),"aria-label":"Filter documentation sections"})}),e.jsxs("nav",{children:[b.map(({s:r,i:a})=>e.jsxs("button",{className:a===o?"on":"",onClick:()=>f(a),type:"button",children:[e.jsx("span",{className:"n",children:r.num||"·"}),e.jsx("span",{children:r.title})]},r.id)),b.length===0&&e.jsxs("div",{className:"no-res",children:["No section matches “",s,"”."]})]})]}),e.jsxs("main",{className:"docpage",children:[e.jsx("h1",{className:"doc-h1",children:"ASTRA · Software Manual"}),e.jsx("div",{className:"doc-content",ref:m,dangerouslySetInnerHTML:{__html:A}}),e.jsxs("div",{className:"doc-pager",children:[u?e.jsxs("button",{onClick:()=>f(o-1),type:"button",children:[e.jsx("span",{className:"dir",children:"← Previous"}),u.num,". ",u.title]}):e.jsx("span",{}),g?e.jsxs("button",{className:"next",onClick:()=>f(o+1),type:"button",children:[e.jsx("span",{className:"dir",children:"Next →"}),g.num,". ",g.title]}):e.jsx("span",{})]})]})]})]})}D(document.getElementById("root")).render(e.jsx(c.StrictMode,{children:e.jsx(j,{})}));
