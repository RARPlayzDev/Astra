import{r as p,j as e,L as h,c as u}from"./styles-owafBBAN.js";const g=`<p>\uFEFF# ASTRA â€” Software Documentation</p>
<p><strong>ASTRA â€” Adaptive Spectrum Threat Recognition &amp; Analysis</strong>
Adaptive scan scheduling for Electronic Support receivers.
Version 1.0.0 Â· SIH 2026 prototype Â· simulation-based research software, not operational equipment.</p>
<hr />
<h2>Contents</h2>
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
</ol>
<hr />
<h2>1. Introduction</h2>
<h3>1.1 What ASTRA is</h3>
<p>ASTRA is a desktop application that schedules the scan pattern of an
Electronic Support (ES) receiver. Such receivers are sensitive but narrowband:
they can listen to only one slice of spectrum at a time while remaining
responsible for a much wider range. Where a conventional receiver sweeps bands
in a fixed pre-mission order, ASTRA decides <strong>where to listen next</strong> based on
what has already been heard â€” surveying the spectrum, learning each emitter's
behaviour, predicting when periodic emitters will transmit again, and
positioning the receiver on those windows before they open.</p>
<h3>1.2 What problem it addresses</h3>
<p>Interception is a two-dimensional search: the receiver must be on the right
frequency at the right time. Fixed scans waste dwell time on empty or
unimportant bands and are slow to return to new or threatening emitters.
Naive adaptivity swings to the opposite failure â€” camping on one busy band and
missing most threats. ASTRA resolves this tension explicitly, achieving both
high reward and high coverage where reference systems achieve only one.</p>
<h3>1.3 What it is not</h3>
<p>ASTRA is a prototype for evaluation. It ships with a physically motivated
simulated RF environment so that it runs anywhere with no hardware; it does not
transmit, jam, or connect to any classified system.</p>
<hr />
<h2>2. Installation</h2>
<h3>2.1 Requirements</h3>
<table>
<thead>
<tr>
<th>Item</th>
<th>Requirement</th>
</tr>
</thead>
<tbody>
<tr>
<td>Operating system</td>
<td>Windows 10/11 (Linux/macOS run from source)</td>
</tr>
<tr>
<td>For <code>ASTRA.exe</code></td>
<td>None beyond the OS; WebView runtime (Edge) ships with Windows</td>
</tr>
<tr>
<td>From source</td>
<td>Python â‰¥ 3.10 with pip; Node.js â‰¥ 18 only if rebuilding the UI</td>
</tr>
</tbody>
</table>
<h3>2.2 Installer (recommended)</h3>
<ol>
<li>Copy or install the <code>ASTRA</code> folder.</li>
<li>Double-click <strong><code>ASTRA.exe</code></strong>. A console window shows service startup, then
   the application window opens.</li>
<li>Closing the application window does not stop the service by itself; use
   <strong>File â†’ Exit</strong> inside ASTRA, or close the console window.</li>
</ol>
<h3>2.3 From source</h3>
<pre><code class="language-powershell">git clone &lt;repository&gt; ; cd p1
python -m pip install -r requirements.txt fastapi uvicorn markdown
cd frontend ; npm install ; npm run build ; cd ..
python desktop.py
</code></pre>
<h3>2.4 Browser-only mode</h3>
<p>Any mode above also works from a normal browser at <code>http://127.0.0.1:&lt;port&gt;</code>
(the port is printed at startup). All features are identical; only the window
frame differs.</p>
<hr />
<h2>3. Quick start</h2>
<ol>
<li>Launch ASTRA (Section 2).</li>
<li>Press <strong>Start Mission</strong> on the toolbar (or File â†’ Start paired mission).</li>
<li>Watch the Operations perspective: two receivers fly identical battlefields;
   blue-grey cells are true transmissions, amber marks intercepts.</li>
<li>Open <strong>Tools â†’ Diagnostics</strong> at any time to verify the installation.</li>
<li>Press <strong>User Guide</strong> on the toolbar whenever you need this document.</li>
</ol>
<hr />
<h2>4. Interface tour</h2>
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
+--------------------------------------------------------------+
</code></pre>
<h3>Menu bar</h3>
<table>
<thead>
<tr>
<th>Menu</th>
<th>Entries</th>
<th>Purpose</th>
</tr>
</thead>
<tbody>
<tr>
<td>File</td>
<td>New mission window Â· Open scenarioâ€¦ Â· Export results (JSON) Â· Exit</td>
<td>Reset the arena, load a battlefield definition, save current benchmarks, shut down</td>
</tr>
<tr>
<td>View</td>
<td>Home Â· Operations Â· Analysis Â· Data &amp; Sources Â· Full screen</td>
<td>Perspective switching</td>
</tr>
<tr>
<td>Run</td>
<td>Start / Stop paired mission Â· Rate presets</td>
<td>Mission control and simulation rate</td>
</tr>
<tr>
<td>Tools</td>
<td>Diagnosticsâ€¦ Â· Open data folder</td>
<td>Self-test of the installation</td>
</tr>
<tr>
<td>Help</td>
<td>User guide Â· About ASTRA</td>
<td>This document; version information</td>
</tr>
</tbody>
</table>
<h3>Toolbar</h3>
<p>Run controls (start/stop), simulation-rate selector, quick access to
Diagnostics and this guide, and the perspective switcher on the right.</p>
<h3>Status bar</h3>
<p>Live state: <code>READY</code> or <code>RUNNING - slot n/T</code>, the product name, the local port,
and a link to the user guide.</p>
<hr />
<h2>5. Operations perspective</h2>
<p>Two panels fly simultaneously:</p>
<ul>
<li><strong>Receiver A â€” SmartScan (adaptive).</strong> Surveys the spectrum, estimates emitter
  rhythms, predicts transmission windows and arrives before they open.</li>
<li><strong>Receiver B â€” sequential sweep (conventional).</strong> Visits every band in fixed
  order, ignoring content â€” standard practice without intelligence.</li>
</ul>
<p>Both receivers experience <strong>byte-identical battlefields</strong> (same emitters, same
noise draws), so any difference in outcome is attributable to scanning strategy
alone.</p>
<p>Waterfall reading:</p>
<table>
<thead>
<tr>
<th>Symbol</th>
<th>Meaning</th>
</tr>
</thead>
<tbody>
<tr>
<td>Blue-grey cell</td>
<td>An emitter truly transmitted on that band in that slot (ground truth)</td>
</tr>
<tr>
<td>Bright vertical band</td>
<td>The band that receiver is currently tuned to</td>
</tr>
<tr>
<td>Amber marker</td>
<td>Confirmed intercept (receiver tuned to a transmitting band)</td>
</tr>
</tbody>
</table>
<p>Per-receiver counters beneath each waterfall update continuously: threat
coverage, threats intercepted (of total present), reward per dwell, hit rate,
false alarms. When an episode completes a result line summarises the A/B
outcome, and the next episode begins automatically on a fresh scenario.</p>
<p>Controls: toolbar <strong>Rate</strong> selects simulation speed (slots per second); rate
affects wall-clock pacing only, never outcomes. <strong>File â†’ Open scenarioâ€¦</strong>
starts a mission on a stored battlefield definition.</p>
<hr />
<h2>6. Analysis perspective</h2>
<p>All values are generated by the bundled experiment suite from stored scenario
seeds; nothing is hand-entered.</p>
<p><strong>KPP gate table.</strong> Each scheduler is first judged against hard Key Performance
Parameters (threat coverage â‰¥ 0.90, prediction accuracy â‰¥ 0.50, false-alarm
rate â‰¤ 5Ã—10â»â´ per slot). Only systems passing every KPP are considered
mission-capable and ranked by the Mission Effectiveness Score (MES).</p>
<p><strong>Monte Carlo table.</strong> Mean Â± 95% confidence intervals across 200 held-out
episodes for reward, threat coverage, prediction accuracy, intercept rate,
false-alarm rate, time-to-first-intercept and intercept-time prediction error.
Paired permutation tests on the gated score separate SmartScan from every
reference policy (p &lt; 1e-4, Holm-Bonferroni corrected).</p>
<p><strong>Evidence gallery.</strong> Generated figures: effectiveness under the gate,
scheduler comparison, training vs held-out greedy evaluation curves, ablation
study, ROC across sensitivity thresholds, geolocation accuracy versus receiver
count.</p>
<p>File â†’ Export results (JSON) writes the full machine-readable payload behind
these tables to disk.</p>
<hr />
<h2>7. Data &amp; Sources perspective</h2>
<p>Three panels manage inputs and artefacts.</p>
<h3>Sensor sources</h3>
<p>Attach live pulse-descriptor-word (PDW) feeds; each attached source reports its
cumulative PDW count and instantaneous rate, proving connectivity before real
hardware is wired in.</p>
<table>
<thead>
<tr>
<th>Type</th>
<th>Parameters</th>
<th>Typical use</th>
</tr>
</thead>
<tbody>
<tr>
<td>UDP feed</td>
<td>port (1024â€“65535), bind address</td>
<td>SDR sweeps, radar processors, <code>tools/pdw_generator.py</code>, <code>tools/sdr_bridge.py</code></td>
</tr>
<tr>
<td>Log file tail</td>
<td>path to growing JSONL/CSV</td>
<td>Third-party equipment writing PDW logs</td>
</tr>
<tr>
<td>Internal simulated scene</td>
<td>band count, seed</td>
<td>Testing with no hardware at all</td>
</tr>
</tbody>
</table>
<p>Detach removes the source cleanly. Errors (for example a busy UDP port or a
missing file) are shown inline on the source row.</p>
<h3>Scenario library</h3>
<p>Every JSON scenario in <code>/scenarios</code> with its band count and horizon. <strong>Fly
paired</strong> starts a new paired mission using that battlefield definition.</p>
<h3>Trained models</h3>
<p>Model artifacts (<code>/models/*.npz</code>) with their policy class, band count and an
integrity verdict. Artifacts are pickle-free NumPy archives validated on load;
a corrupt file is flagged here rather than executed.</p>
<hr />
<h2>8. Radar and sensor integration</h2>
<h3>8.1 Integration contract</h3>
<p>ASTRA consumes standard ESM measurements â€” <strong>pulse descriptor words</strong>:</p>
<pre><code class="language-json">{&quot;toa_us&quot;: 1000.0, &quot;freq_mhz&quot;: 9450.0, &quot;pw_us&quot;: 1.5, &quot;pa_db&quot;: 12.0, &quot;aoa_deg&quot;: 90.0}
</code></pre>
<table>
<thead>
<tr>
<th>Field</th>
<th>Meaning</th>
<th>Required</th>
</tr>
</thead>
<tbody>
<tr>
<td><code>toa_us</code></td>
<td>time of arrival, microseconds</td>
<td>yes</td>
</tr>
<tr>
<td><code>freq_mhz</code></td>
<td>centre frequency, MHz</td>
<td>yes</td>
</tr>
<tr>
<td><code>pw_us</code></td>
<td>pulse width, Âµs</td>
<td>optional (default 1.0)</td>
</tr>
<tr>
<td><code>pa_db</code></td>
<td>amplitude, dB</td>
<td>optional</td>
</tr>
<tr>
<td><code>aoa_deg</code></td>
<td>angle of arrival, degrees</td>
<td>optional</td>
</tr>
</tbody>
</table>
<p>Datagrams may carry <strong>one JSON object or a JSON array</strong> of objects. A single
datagram per pulse-group per slot is the intended cadence (default slot =
1 ms), but the pipeline tolerates bursty delivery and re-bins by <code>toa_us</code>.</p>
<h3>8.2 Wiring any radar / SDR processor</h3>
<p>Three supported paths, in increasing fidelity:</p>
<ol>
<li><strong>Synthetic generator (no hardware).</strong>
   <code>python tools/pdw_generator.py --port 5555 --rate 400</code>
   emits realistic multi-emitter traffic over UDP for integration testing.</li>
<li><strong>Bridge an existing sweep log.</strong>
   <code>python tools/sdr_bridge.py --mode csv --csv sweep.csv --out-port 5555</code>
   converts CSV sweeps (or relays an existing JSON feed with <code>--mode udp</code>) into
   the ASTRA datagram format.</li>
<li><strong>Direct emission.</strong> Your processor writes the JSON schema above straight to
   ASTRA's UDP port (attach the source in <strong>Data &amp; Sources</strong>, then select the
   same port).</li>
</ol>
<h3>8.3 Adapting exotic front-ends</h3>
<p>If your equipment produces another format, write a ~30-line adapter that maps
it onto the five-field PDW schema and forwards datagrams â€” see
<code>tools/sdr_bridge.py</code> as the template. Channelised or FFT-based receivers can
emit one PDW per detected peak per dwell.</p>
<h3>8.4 Notes and limits</h3>
<ul>
<li>Frequency-to-band mapping uses the scenario's <code>[fmin, fmax]</code>; out-of-range
  frequencies clamp to the edge bands.</li>
<li>The demo pipeline assumes a single receiver location; AOA is carried end to
  end for identification and geolocation studies.</li>
<li>No data leaves the machine: all networking is local loopback unless you bind
  otherwise deliberately.</li>
</ul>
<hr />
<h2>9. Scenarios</h2>
<p>A scenario is a JSON file in <code>/scenarios</code>. Key fields (all optional):</p>
<table>
<thead>
<tr>
<th>Field</th>
<th>Default</th>
<th>Meaning</th>
</tr>
</thead>
<tbody>
<tr>
<td><code>n_bands</code></td>
<td>24</td>
<td>number of frequency bins</td>
</tr>
<tr>
<td><code>T</code></td>
<td>3000</td>
<td>episode length in slots</td>
</tr>
<tr>
<td><code>seed</code></td>
<td>0</td>
<td>reproducibility seed</td>
</tr>
<tr>
<td><code>n_stationary</code> / <code>n_agile</code> / <code>n_periodic</code> / <code>n_spatial</code> / <code>n_clutter</code></td>
<td>6/4/4/3/8</td>
<td>emitter mix</td>
</tr>
<tr>
<td><code>snr_mean_db</code>, <code>snr_std_db</code></td>
<td>12 / 4</td>
<td>signal strength distribution</td>
</tr>
<tr>
<td><code>freq_min_mhz</code>, <code>freq_max_mhz</code></td>
<td>2000â€“18000</td>
<td>tuning range</td>
</tr>
<tr>
<td><code>period_range</code>, <code>on_len_range</code>, <code>dwell_range</code>, <code>hop_set_range</code></td>
<td>class priors</td>
<td>behavioural ranges</td>
</tr>
</tbody>
</table>
<p>Scenario + seed â‡’ exactly reproducible battlefield.</p>
<hr />
<h2>10. Datasets and calibration</h2>
<p>ASTRA honours the referenced datasets:</p>
<ul>
<li><strong>JC Wise, Radar Emitter Database (2024)</strong> â€” basis of the identification
  library profiles used to tag intercepted streams.</li>
<li><strong>Alan Turing Institute synthetic radar dataset (HuggingFace)</strong> â€” imported by
  Dataset Studio (Streamlit dashboard) online when reachable, with a
  schema-identical offline fallback so everything works air-gapped.</li>
</ul>
<p>Imported PDWs drive scenario calibration: observed frequency clusters become
emitters, and their temporal statistics set behavioural classes.</p>
<hr />
<h2>11. Scheduling policies</h2>
<p>Seven policies ship with the system; six exist as honest references:</p>
<table>
<thead>
<tr>
<th>Name</th>
<th>Class</th>
<th>Character</th>
</tr>
</thead>
<tbody>
<tr>
<td>Sequential sweep</td>
<td>open loop</td>
<td>fixed cyclic visitation</td>
</tr>
<tr>
<td>Random scan</td>
<td>open loop</td>
<td>uniform random selection</td>
</tr>
<tr>
<td>Priority sweep</td>
<td>open loop</td>
<td>prior-intelligence ordering</td>
</tr>
<tr>
<td>UCB bandit</td>
<td>adaptive, exploit-only</td>
<td>converges on richest band (demonstrates the exploit trap)</td>
</tr>
<tr>
<td>Linear Q-learning</td>
<td>reinforcement learning</td>
<td>learned value over hand-crafted features</td>
</tr>
<tr>
<td>Deep Q-network</td>
<td>deep RL</td>
<td>MLP + replay + target network</td>
</tr>
<tr>
<td><strong>SmartScan</strong></td>
<td>proposed hybrid</td>
<td>five behaviours multiplexed by learned confidence</td>
</tr>
</tbody>
</table>
<p>SmartScan's behaviours: reconnaissance sweep; cued pursuit of validated phase
locks; predict-and-probe of candidate rhythms; characterisation bursts;
value-weighted rotation with recency guarantees and an exploitation ramp.
Locks require repeated mutually isolated detections on one SNR+AOA fingerprint
and are deleted automatically after repeated failed predictions.</p>
<hr />
<h2>12. Evaluation methodology</h2>
<p>Following defence test &amp; evaluation practice:</p>
<ol>
<li><strong>KPPs (hard gates).</strong> Threat coverage â‰¥ 0.90 Â· prediction accuracy â‰¥ 0.50 Â·
   false alarms â‰¤ 5Ã—10â»â´/slot. Failing any gate â‡’ <em>not mission-capable</em>.</li>
<li><strong>MES ranking.</strong> Among capable systems, mean of six normalised
   problem-statement figures of merit (Pd, Pfa performance, intercept rate,
   reward, prediction accuracy, intercept-time error).</li>
<li><strong>Statistics.</strong> Paired per-episode permutation tests on the gated score with
   Holm-Bonferroni correction; 200 held-out episodes; 95% confidence intervals.</li>
</ol>
<p>Headline outcome: <strong>SmartScan is the only mission-capable scheduler in the
field</strong> and leads every comparator at p &lt; 1e-4 on gated MES. Learning claims
are backed by held-out greedy evaluation; the deep-network reference's decline
on this sparse task is reported as measured.</p>
<p>Regenerate everything:</p>
<pre><code class="language-powershell">python -m ewsmart.experiments --suite full
</code></pre>
<hr />
<h2>13. Diagnostics and troubleshooting</h2>
<p><strong>Tools â†’ Diagnostics</strong> verifies the installation: module imports, environment
boot, benchmark presence, figure inventory, model-artifact integrity, frontend
bundle, manual availability and a UDP loopback test.</p>
<table>
<thead>
<tr>
<th>Symptom</th>
<th>Likely cause</th>
<th>Remedy</th>
</tr>
</thead>
<tbody>
<tr>
<td>Window opens blank</td>
<td>frontend bundle missing</td>
<td>rebuild: <code>cd frontend &amp;&amp; npm run build</code></td>
</tr>
<tr>
<td>"Benchmark data: not generated" on Home</td>
<td>suite never ran</td>
<td>run the experiment suite command above</td>
</tr>
<tr>
<td>Source row shows <code>WinError 10048</code></td>
<td>UDP port already bound</td>
<td>choose another port; stop the other process</td>
</tr>
<tr>
<td>Source attaches but 0 PDWs</td>
<td>no sender / wrong port / firewall</td>
<td>start <code>tools/pdw_generator.py --port &lt;same&gt;</code>; allow python through the firewall</td>
</tr>
<tr>
<td>Analysis empty after export</td>
<td>results file absent</td>
<td>regenerate via experiment suite</td>
</tr>
<tr>
<td>Exit did nothing</td>
<td>popup blocked for <code>window.close()</code></td>
<td>close the console window; service stops with it</td>
</tr>
</tbody>
</table>
<hr />
<h2>14. Testing without a radar</h2>
<p>Full instructions in <a href="../HOW_TO_TEST.md"><code>HOW_TO_TEST.md</code></a>. Summary ladder:</p>
<ol>
<li><strong>Automated tests</strong> â€” 50 backend + 7 interface tests, each runnable standalone.</li>
<li><strong>In-app diagnostics</strong> â€” Tools â†’ Diagnostics.</li>
<li><strong>Internal simulated scene source</strong> â€” attach in Data &amp; Sources; counts PDWs with zero hardware.</li>
<li><strong>UDP generator</strong> â€” <code>tools/pdw_generator.py</code> streams realistic emitter traffic to a chosen port.</li>
<li><strong>CSV replay bridge</strong> â€” <code>tools/sdr_bridge.py</code> replays recorded sweeps.</li>
<li><strong>Paired missions</strong> â€” statistical A/B evidence at any simulation rate.</li>
</ol>
<p>Recommended edge cases: malformed datagrams (ignored gracefully), burst floods,
empty feeds (source stays healthy, zero counts), port conflicts (inline error),
scenario extremes (few bands, short horizons), repeated start/stop cycling, two
browser windows sharing one service.</p>
<hr />
<h2>15. Architecture reference</h2>
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
docs/                 this document
</code></pre>
<hr />
<h2>16. Local API reference</h2>
<p>All endpoints are local-first (<code>127.0.0.1</code>). Interactive OpenAPI UI: <code>/api-docs</code>.</p>
<table>
<thead>
<tr>
<th>Method &amp; path</th>
<th>Purpose</th>
</tr>
</thead>
<tbody>
<tr>
<td>GET <code>/api/meta</code></td>
<td>name, version, availability flags</td>
</tr>
<tr>
<td>GET <code>/api/health</code></td>
<td>liveness probe</td>
</tr>
<tr>
<td>GET <code>/api/summary</code></td>
<td>full benchmark payload</td>
</tr>
<tr>
<td>GET <code>/api/figures</code> Â· <code>/api/figures/{name}.png</code></td>
<td>figure inventory and images</td>
</tr>
<tr>
<td>GET <code>/api/scenarios</code></td>
<td>scenario library</td>
</tr>
<tr>
<td>POST <code>/api/live/start?speed&amp;scenario</code></td>
<td>start paired mission (optionally from a named scenario)</td>
</tr>
<tr>
<td>POST <code>/api/live/stop</code></td>
<td>stop mission</td>
</tr>
<tr>
<td>GET <code>/api/live/status</code></td>
<td>running flag, slot, per-scheduler KPIs</td>
</tr>
<tr>
<td>GET <code>/api/live/stream</code></td>
<td>SSE frame stream</td>
</tr>
<tr>
<td>GET/POST/DELETE <code>/api/sources</code></td>
<td>sensor source management</td>
</tr>
<tr>
<td>GET <code>/api/models</code></td>
<td>model artifacts + integrity</td>
</tr>
<tr>
<td>GET <code>/api/diagnostics</code></td>
<td>self-test checklist</td>
</tr>
<tr>
<td>GET <code>/manual</code></td>
<td>rendered user guide</td>
</tr>
<tr>
<td>POST <code>/api/shutdown</code></td>
<td>graceful shutdown (used by File â†’ Exit)</td>
</tr>
</tbody>
</table>
<hr />
<h2>17. Command-line tools</h2>
<table>
<thead>
<tr>
<th>Command</th>
<th>Purpose</th>
</tr>
</thead>
<tbody>
<tr>
<td><code>python desktop.py</code></td>
<td>launch the desktop application</td>
</tr>
<tr>
<td><code>python -m ewsmart.runner --scenario scenarios/demo.json --save-dir models --json-out results.json</code></td>
<td>train + evaluate one scenario</td>
</tr>
<tr>
<td><code>python -m ewsmart.experiments --suite full</code></td>
<td>regenerate all published results</td>
</tr>
<tr>
<td><code>python tools/pdw_generator.py --port 5555 --rate 400</code></td>
<td>synthetic PDW feed over UDP</td>
</tr>
<tr>
<td><code>python tools/sdr_bridge.py --mode csv --csv sweep.csv --out-port 5555</code></td>
<td>bridge CSV/JSON sweeps into ASTRA format</td>
</tr>
<tr>
<td><code>powershell -File tools/build_exe.ps1</code></td>
<td>build <code>dist/ASTRA/ASTRA.exe</code></td>
</tr>
</tbody>
</table>
<hr />
<h2>18. File formats</h2>
<p><strong>Scenario JSON</strong> â€” fields per Section 9.</p>
<p><strong>PDW datagram</strong> â€” Section 8.1.</p>
<p><strong>Model artifact (.npz)</strong> â€” <code>meta</code> = JSON string <code>{format:"ewsmart-npz-v1",
class, n_bands, ...}</code> plus plain arrays; loaded with <code>allow_pickle=False</code>.</p>
<p><strong>results/suite_results.json</strong> â€” sections: <code>monte_carlo</code>, <code>significance</code>,
<code>mission_effectiveness</code>, <code>significance_gated_mes</code>, <code>learning</code>,
<code>identification</code>, <code>roc</code>, <code>sensitivity</code>, <code>ablation</code>, <code>multireceiver</code>,
<code>geolocation</code>.</p>
<hr />
<h2>19. Frequently asked questions</h2>
<p><strong>Does closing the app window stop the service?</strong> Use File â†’ Exit for a clean
shutdown; the console window also stops the service when closed.</p>
<p><strong>Can several windows share one service?</strong> Yes â€” open additional browser tabs
to the printed URL; all views stay in sync because state lives server-side.</p>
<p><strong>Where do numbers come from?</strong> Experiments over stored seeds; re-run the suite
to reproduce byte-for-byte.</p>
<p><strong>Is any data sent to the internet?</strong> No. Networking is loopback except an
optional HuggingFace fetch inside Dataset Studio, which falls back offline.</p>
<p><strong>Why does Receiver B exist?</strong> Controlled comparison. Identical battlefields
make the strategy the only variable.</p>
<hr />
<h2>20. Glossary</h2>
<table>
<thead>
<tr>
<th>Term</th>
<th>Meaning</th>
</tr>
</thead>
<tbody>
<tr>
<td>ES / ESM</td>
<td>Electronic Support â€” passive search, intercept, analysis of emissions</td>
</tr>
<tr>
<td>PDW</td>
<td>Pulse Descriptor Word (TOA, frequency, width, amplitude, AOA)</td>
</tr>
<tr>
<td>Dwell</td>
<td>One listening interval on one band</td>
</tr>
<tr>
<td>Slot</td>
<td>Discrete time step of the simulation (default 1 ms)</td>
</tr>
<tr>
<td>Phase lock (ASTRA)</td>
<td>Validated estimate of a periodic emitter's period and window timing</td>
</tr>
<tr>
<td>KPP</td>
<td>Key Performance Parameter â€” hard pass/fail requirement</td>
</tr>
<tr>
<td>MES</td>
<td>Mission Effectiveness Score â€” composite FoM after gating</td>
</tr>
<tr>
<td>CEP</td>
<td>Circular Error Probable â€” median geolocation error radius</td>
</tr>
</tbody>
</table>`,n=[{id:"1-introduction",title:"Introduction",heading:"1. Introduction"},{id:"2-installation",title:"Installation",heading:"2. Installation"},{id:"3-quick-start",title:"Quick Start",heading:"3. Quick start"},{id:"4-interface-tour",title:"Interface Tour",heading:"4. Interface tour"},{id:"5-operations-perspective",title:"Operations",heading:"5. Operations perspective"},{id:"6-analysis-perspective",title:"Analysis",heading:"6. Analysis perspective"},{id:"7-data--sources-perspective",title:"Data & Sources",heading:"7. Data &amp; Sources perspective"},{id:"8-radar-and-sensor-integration",title:"Sensor Integration",heading:"8. Radar and sensor integration"},{id:"9-scenarios",title:"Scenarios",heading:"9. Scenarios"},{id:"10-datasets-and-calibration",title:"Datasets & Calibration",heading:"10. Datasets and calibration"},{id:"11-scheduling-policies",title:"Scheduling Policies",heading:"11. Scheduling policies"},{id:"12-evaluation-methodology",title:"Evaluation",heading:"12. Evaluation methodology"},{id:"13-diagnostics-and-troubleshooting",title:"Diagnostics",heading:"13. Diagnostics and troubleshooting"},{id:"14-testing-without-a-radar",title:"Testing",heading:"14. Testing without a radar"},{id:"15-architecture-reference",title:"Architecture",heading:"15. Architecture reference"},{id:"16-local-api-reference",title:"API Reference",heading:"16. Local API reference"},{id:"17-command-line-tools",title:"CLI Tools",heading:"17. Command-line tools"},{id:"18-file-formats",title:"File Formats",heading:"18. File formats"},{id:"19-frequently-asked-questions",title:"FAQ",heading:"19. Frequently asked questions"},{id:"20-glossary",title:"Glossary",heading:"20. Glossary"}];function m(t,i){const s=[`<h2>${i.heading}</h2>`,`<h2>${i.heading.replace(/&amp;/g,"&")}</h2>`];let r=-1;for(const a of s)if(r=t.indexOf(a),r!==-1)break;if(r===-1){const a=i.heading.replace(/&amp;/g,"&").replace(/^\d+\.\s*/,""),c=/<h2>([^<]+)<\/h2>/g;let o;for(;(o=c.exec(t))!==null;)if(o[1].includes(a)||o[1]===i.heading){r=o.index;break}}if(r===-1)return"<p>Section content not available.</p>";const d=t.indexOf("<h2>",r+10),l=d!==-1?d:t.length;return t.slice(r,l).replace(/<hr\s*\/?>/g,"").trim()}function f(){const[t,i]=p.useState(0),s=p.useRef(null);p.useEffect(()=>{s.current&&(s.current.scrollTop=0)},[t]);const r=n[t],d=m(g,r),l=t>0?n[t-1]:null,a=t<n.length-1?n[t+1]:null;return e.jsxs("div",{style:{display:"flex",flexDirection:"column",height:"100%",background:"#1e1e1e"},children:[e.jsxs("div",{style:{display:"flex",alignItems:"center",gap:16,background:"#252526",borderBottom:"1px solid #3c3c3c",padding:"10px 24px",flexShrink:0},children:[e.jsxs("a",{href:"/",style:{display:"flex",alignItems:"center",gap:8,textDecoration:"none"},children:[e.jsx(h,{size:22}),e.jsx("span",{style:{fontFamily:"monospace",fontWeight:700,color:"#ccc",letterSpacing:2,fontSize:13},children:"ASTRA"})]}),e.jsx("span",{style:{color:"#858585",fontSize:13},children:"Documentation — v2.0.0"}),e.jsxs("div",{style:{marginLeft:"auto",display:"flex",gap:10},children:[e.jsx("a",{href:"/docs/manual.md",download:!0,style:{padding:"6px 14px",fontSize:12,border:"1px solid #3c3c3c",borderRadius:3,color:"#ccc",textDecoration:"none",background:"#2d2d30"},children:"Download (.md)"}),e.jsx("a",{href:"/",style:{padding:"6px 14px",fontSize:12,background:"#264f78",borderRadius:3,color:"#fff",textDecoration:"none"},children:"Back to site"})]})]}),e.jsxs("div",{style:{display:"flex",flex:1,overflow:"hidden"},children:[e.jsxs("nav",{style:{width:220,flexShrink:0,background:"#252526",borderRight:"1px solid #3c3c3c",overflowY:"auto",padding:"12px 0"},children:[e.jsx("div",{style:{fontSize:10,fontWeight:700,letterSpacing:1.5,textTransform:"uppercase",color:"#858585",padding:"4px 16px 10px"},children:"Table of Contents"}),n.map((c,o)=>e.jsx("button",{onClick:()=>i(o),style:{display:"block",width:"100%",textAlign:"left",background:t===o?"#264f78":"transparent",border:"none",color:t===o?"#fff":"#999",padding:"7px 16px",fontSize:13,cursor:"pointer",fontFamily:"inherit",borderLeft:t===o?"2px solid #5aa0e9":"2px solid transparent"},children:c.title},c.id))]}),e.jsxs("div",{ref:s,style:{flex:1,overflowY:"auto",padding:"28px 44px 60px",maxWidth:800},children:[e.jsx("div",{className:"doc-content",dangerouslySetInnerHTML:{__html:d}}),e.jsxs("div",{style:{display:"flex",justifyContent:"space-between",marginTop:48,paddingTop:20,borderTop:"1px solid #3c3c3c"},children:[l?e.jsxs("button",{onClick:()=>i(t-1),style:{background:"none",border:"1px solid #3c3c3c",borderRadius:4,padding:"8px 18px",color:"#999",cursor:"pointer",fontSize:13},children:["← ",l.title]}):e.jsx("div",{}),a?e.jsxs("button",{onClick:()=>i(t+1),style:{background:"#264f78",border:"none",borderRadius:4,padding:"8px 18px",color:"#fff",cursor:"pointer",fontSize:13},children:[a.title," →"]}):e.jsx("div",{})]})]})]})]})}u(document.getElementById("root")).render(e.jsx(p.StrictMode,{children:e.jsx(f,{})}));
