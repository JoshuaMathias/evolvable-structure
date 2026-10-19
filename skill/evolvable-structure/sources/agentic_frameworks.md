# AI and agentic frameworks related to ESOI (research record)

Researched and accessed 2026-10-17. Companion to `public_research.md` (which covers modularity, variability, evolutionary architecture including Ford, Parsons and Kua fitness functions, cybernetics, and counter-evidence; not repeated here). The readable public version is `docs/explanation/related-work.md` in the public ESOI repository.

Verification key: V-page = the primary page was fetched and read through a summarising fetch tool (so quotes are as returned by that tool, not copied from raw HTML); V-abs = arXiv abstract page read; NV = could not be fetched or confirmed, content below is background knowledge and marked as such. Ideal numbers refer to SKILL.md principles 1 to 13 (4 = automatic best implementation, humans need only review metrics but can still add value to implementations; 2 = ontology and when to split; 7 = humility).

## 1. Layered models of trustworthy agents

### Sarah Payne, "The Agentic Integrity Stack" (sarahpayne.ai)
Link: https://www.sarahpayne.ai/the-agentic-integrity-stack (V-page, 2026-10-17). Page says "last updated June 2026"; the header says v1.1 but the changelog describes v1.2; no original publication date. The author says it is not yet tested at full production scale.
What it is: a systems-level design checklist for agents that act autonomously but stay controllable. Six layers, each with definition, why it matters, common failure and a "working signal": (1) Scoped Purpose, (2) Bounded Tool Access, (3) Planning and Replanning Logic, (4) Fallback and Escalation Paths, (5) Structured Memory, (6) Interrupt Logic. Three supporting mechanisms: Adaptive Constraint Calibration (constraints adapt on behavioural evidence such as approval and override rates plus operational economics; structural layers such as Scoped Purpose, Interrupt Logic and Fallback do not adapt; changes need human or policy approval, bounded scope and a logged reversible trail), Cross-Agent Authority Resolution (one system-of-record agent per overlapping case, fixed at design time, "not earned through performance"), Semantic Outcome Reconciliation (compare actual post-execution state with verifiable goal criteria, "state, not process"). The author's typology: "calibration adapts, authority is fixed, and reconciliation verifies."
Quotes: "Agents don't just need intelligence, they need integrity." "Integrity isn't about parts. It's about how parts govern each other in motion." (the source uses an em dash in the first; rendered with a comma here).
Shares with ESOI: scoped purpose (a Solution's "Scoped Purpose" and what it avoids); checking real outcomes rather than process (principle 10, "the real thing, the problem solved in the wild"); an explicit choice of what is stable (structural layers) and what adapts (principles 1, 5); observable "working signal" is close to a Hint of Measurement on an Ideal.
Differs: it is a runtime checklist for one agent, not a record network; no alternative implementations and no metric-driven selection; calibration adapts constraints, not implementations; no problem or ideal records. Not a competitor, a complementary diagnostic.
Borrow: a one-line observable "working signal" for every Solution or Ideal; the rule that the loop which tunes things must not tune its own safeguards (keep the metric-run policy and the approval rules outside the selection loop); fixed authority for overlapping solutions (which solution owns an overlapping case).
Evidence: practitioner design note, one author, untested at scale by her own statement.

## 2. Spec-driven and intent-driven development, context files

### GitHub Spec Kit
Link: https://github.com/github/spec-kit (V-page). Flow: constitution (project principles), specify, plan, tasks, implement, plus a converge command to repeat until "Converged". Quote: "Define what and why before deciding how to build it." The page does not discuss producing multiple implementations of a spec (confirmed by the fetch; not found, not proven absent elsewhere in the repo).
Shares: why and what before how (principle 2: solutions say what, not how); a constitution is like top-level ideals.
Differs: one document chain per feature, no ontology of problem, ideal, solution; no alternatives; no metric chooses; review is on generated artifacts.
Borrow: the constitution as a short always-loaded statement of ideals; a converge step (loop until the checks pass) as a named stage.

### Kiro specs
Link: https://kiro.dev/docs/specs/ (V-page). Three files per spec: requirements.md (user stories, acceptance criteria or bug analysis "in structured notation"; bugfix specs record current, expected and unchanged behaviour), design.md, tasks.md with dependency-based parallel waves. The page lists "Correctness (property-based testing)" as IDE-only capability and does not mention EARS notation (so EARS is not confirmed here, although Kiro is widely reported to use it; NV).
Shares: acceptance criteria are close to Measures of Success; "unchanged behaviour" for bugs is an invariant solution in ESOI terms.
Differs: per feature, one implementation.
Borrow: bugfix records of "current, expected, unchanged" as a template for invariants.

### Birgitta Bockeler, "Understanding Spec-Driven-Development: Kiro, spec-kit, and Tessl" (Thoughtworks, on martinfowler.com, 15 October 2025)
Link: https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html (V-page). Three levels: spec-first (spec guides one task then is set aside), spec-anchored (spec persists and evolves), spec-as-source (humans edit only the spec; code carries "GENERATED FROM SPEC - DO NOT EDIT"). Her findings: all tools are spec-first, maintenance strategy vague; Kiro overkill for a small bug ("4 user stories with a total of 16 acceptance criteria"); Spec Kit produced verbose markdown she found harder to review than code, and agents ignored notes and made duplicates; Tessl regenerating from the same spec "produced different results"; MDD parallel: "Inflexibility and non-determinism". Quote: "Are we making something worse in the attempt of making it better?"
Relevance: the strongest outside statement of two ESOI points. A spec cannot say which of several outputs is better (a metric is needed), and review burden shifts to artifacts unless something selects automatically (principle 4). Also supports principle 2's "when to split": one workflow does not fit all sizes.
Borrow: vocabulary spec-first, anchored, source to describe how binding each record is.

### AGENTS.md
Link: https://agents.md (V-page). Open Markdown format "a README for agents", now stewarded by the Agentic AI Foundation under the Linux Foundation, emerged from OpenAI Codex, Amp, Google Jules, Cursor, Factory. Nested files in monorepos; "The closest AGENTS.md to the edited file wins; explicit user chat prompts override everything." The page cites 88 files in the main OpenAI repository at the time of writing.
Shares: nearest-context-wins and per-folder files match "specify only what is different" (principles 9, 12, 13) and a context file per folder.
Differs: instructions, not intent records; nothing measured.
Borrow: nothing new; confirms the convention (the CLAUDE.md equivalent) is converging across vendors.

### Anthropic, "Effective context engineering for AI agents"
Link: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents (V-page). Definition: "the set of strategies for curating and maintaining the optimal set of tokens" at inference. Techniques: right-altitude system prompts, token-efficient tools, few-shot canonical examples, just-in-time retrieval, compaction, structured note-taking, sub-agents. Goal: "the smallest set of high-signal tokens".
Shares: read only what is necessary at a given moment (principle 13).
Differs: strategies are not compared by a recorded metric on the page.
Borrow: treat context assembly as a Solution whose alternatives (retrieve up front, just in time, compact) are compared by metric.

### Anthropic, "Building effective agents"
Link: https://www.anthropic.com/engineering/building-effective-agents (V-page). Workflows (predefined code paths: chaining, routing, parallelisation, orchestrator-workers) versus agents (model decides its steps). Evaluator-optimizer loop for when "clear evaluation criteria" exist. Quotes: "finding the simplest solution possible, and only increasing complexity when needed"; "measuring performance and iterating on implementations."
Shares: add complexity only when it demonstrably improves outcomes is the same trade as the split rule in principle 2 and simplicity in 12; the evaluator-optimizer needs criteria, which ESOI records as the ideal and metric.
Differs: a pattern catalogue, not a record structure.

## 3. Eval-driven development and metric-selected implementations

### DSPy
Links: paper https://arxiv.org/abs/2310.03714 (V-abs; Khattab et al.); README https://raw.githubusercontent.com/stanfordnlp/dspy/main/README.md (V-page). The docs site pages for signatures and optimizers (dspy.ai/learn/...) returned only a redirect stub when fetched, so those pages are NV; the signature-as-interface and optimizer descriptions below rest on the paper abstract and README plus background knowledge.
What it is: a programming model where LM pipelines are "text transformation graphs" of declarative, parameterised modules, and "a compiler optimizes a DSPy pipeline toward a specified metric". README tagline: "programming, rather than prompting, language models"; optimizers improve prompts and weights ("Declarative Self-improving Python"). Reported: self-bootstrapped pipelines beat standard few-shot prompting and expert-written demonstrations; a 770M T5 compiled with DSPy competitive with expert prompt chains on GPT-3.5.
Shares: very close to Solution (signature as interface: inputs, outputs, purpose), Implementation (the optimizer-chosen prompt and demonstrations), Metric (a function the compiler optimizes). Principle 4 in code: the implementation is chosen by metric, not by reading.
Differs: the search space is the implementation of one fixed interface; no Problem or Ideal records, no rule for when to split an interface, the metric is an input rather than a replaceable solution, and no network linking solutions. The structure does not evolve itself.
Borrow: define the interface once and let the optimizer fill the implementation; keep optimizer runs as recorded alternatives with the metric and case hash.

### GEPA
Link: https://arxiv.org/abs/2507.19457 (V-abs; Agrawal et al., ICLR 2026 oral per the page). Genetic-Pareto prompt optimizer that reflects on trajectories in natural language and combines lessons from the Pareto frontier of its attempts. Reported: beats GRPO by 6% on average (up to 20%) with up to 35x fewer rollouts; beats MIPROv2 by over 10%.
Borrow: Pareto frontier when two ideals (cost versus accuracy) pull apart, instead of one number. ESOI's verdicts already use pass rate then spend; a frontier is the generalisation.

### TextGrad
Link: https://arxiv.org/abs/2406.07496 (V-abs; Yuksekgonul et al., 2024). Backpropagates LLM-written textual feedback to improve components; user supplies an objective function. Reported gains include roughly 20% relative on LeetCode-Hard and higher zero-shot GPT-4o accuracy on GPQA.
Relevance: same shape as DSPy: objective function in, improved component out. Feedback text itself is evidence about the implementation worth recording.

### EvoPrompt
Link: https://arxiv.org/abs/2309.08532 (V-abs; Guo et al., ICLR 2024). LLM applies evolutionary operators to prompt populations scored on a development set; 31 datasets; up to 25% over earlier automatic prompt generation on BBH.

### Eureka and Voyager
Eureka https://arxiv.org/abs/2310.12931 (V-abs): LLM-driven evolutionary search over reward code, rewards beat expert-designed ones on 83% of 29 tasks. Voyager https://arxiv.org/abs/2305.16291 (V-abs): "an ever-growing skill library of executable code". Both show alternatives written as code and selected by a task score; Voyager's library is a reusable-structure store (principle 8).

### Evaluation harnesses and practice
- Inspect (UK AI Security Institute and Meridian Labs): https://inspect.aisi.org.uk/ (V-page). A Task = Dataset + Solver + Scorer; a solver can be one call or a multi-turn agent. Maps to cases, implementation, metric scoring.
- Promptfoo: https://www.promptfoo.dev/docs/intro/ (V-page). "test-driven LLM development, not trial-and-error"; matrix view across prompts, "to choose the best model and prompt". This is alternatives compared on the same cases, which is exactly the ESOI comparison, but selection is by a human reading the matrix.
- Anthropic, "Demystifying evals for AI agents": https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents (V-page). Code, model and human graders; capability evals start low, regression evals sit near 100%, capability evals "graduate"; "A 0% pass rate across many trials is most often a signal of a broken task, not an incapable agent"; test both when behaviour should and should not occur; watch for saturation; calibrate judges against humans, give them an "Unknown" option; start with 20 to 50 tasks from real failures; combine evals with production monitoring.
- Hamel Husain, "Your AI Product Needs Evals": https://hamel.dev/blog/posts/evals/ (V-page). "success with AI hinges on how fast you can iterate"; "you can never stop looking at data"; validate LLM judges against humans and track precision and recall, not just raw agreement.
- Zheng et al., "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena": https://arxiv.org/abs/2306.05685 (V-abs). GPT-4 judge reaches "over 80% agreement, the same level of agreement between humans"; position, verbosity and self-enhancement biases.
- OpenAI Evals ("evals as specs"): https://openai.com/index/evals/ returned HTTP 403, so NV. Background only: the evals framework and registry, and the idea that an eval is an executable statement of desired behaviour; not cited in the public page.
Shares: Metric is exactly cases plus a scorer (choosing-by-metric.md). Capability versus regression matches eval versus invariant solutions in ESOI.
Differs: practices and tools for measuring; none says the winner runs automatically, which solution a result belongs to, or that the metric is itself a solution with versions.
Borrow: graduation of a passing capability eval into a regression invariant; saturation as a trigger to revise the metric; a judge-validation arm (ESOI already has "validity" arms; this is the same idea with a human-agreement target); "Unknown" option for judges.

## 4. Self-improving and evolutionary agent systems

### AlphaEvolve
Link: https://arxiv.org/abs/2506.13131 (V-abs; Novikov et al., 2025). Evolutionary coding agent where LLMs edit code over many iterations using feedback from one or more evaluators. Results reported: data-centre scheduling heuristic, a simpler hardware circuit, 4x4 complex matrix multiplication with 48 scalar multiplications (first improvement over Strassen in that setting in 56 years, per the page).
Requires: a machine-checkable evaluator. That is the precondition for principle 4 and it explains why ESOI asks for a practical metric per solution.

### OpenEvolve
Link: https://github.com/algorithmicsuperintelligence/openevolve (V-page). Open-source AlphaEvolve implementation. Evaluator returns metrics and artifacts (stderr, profiling, build warnings) that feed the next prompt; cascade evaluation in stages; MAP-Elites quality-diversity grid; island populations with migration to avoid premature convergence.
Borrow: cascade evaluation is the staged 3, 10, 30 sample in `when-metrics-are-run.md`; evaluator artifacts (why it failed) recorded beside the score; diversity preservation so a niche alternative survives if it wins a different use case (a hint toward splitting).

### Darwin Godel Machine
Link: https://arxiv.org/abs/2505.22954 (V-abs; Zhang, Hu, Lu, Lange, Clune; v3 March 2026). Self-rewriting coding agent with an archive; samples an agent, a foundation model makes a variant, benchmarks validate. SWE-bench 20.0% to 50.0%, Polyglot 14.2% to 30.7% (reported). Validates empirically "rather than proving"; experiments run with sandboxing and human oversight.
Shares: the structure improves itself (principle 5) and an archive of alternatives; validation by metric rather than by reading.
Differs: the benchmark is fixed and trusted. ESOI's principle 7 says even the metric is a limited approximation; DGM does not address benchmark gaming here (not stated on the page).
Borrow: keep the archive of past alternatives as stepping stones, not only the selected one.

### ADAS (Automated Design of Agentic Systems)
Link: https://arxiv.org/abs/2408.08435 (V-abs; Hu, Lu, Clune). A meta agent programs new agents in code, drawing on an archive (Meta Agent Search). Reported: discovered agents beat state-of-the-art hand-designed ones on coding, science and math and transferred across domains and models. Quote: "hand-designed solutions are eventually replaced by learned solutions."
Relevance: the structure-level analogue; the interface (an agent defined in code) is fixed and the implementations are searched.

### AFlow
Link: https://arxiv.org/abs/2410.10762 (V-abs; Zhang et al.). Workflow optimisation as search over code-represented workflows with Monte Carlo Tree Search; 5.7% average gain over baselines across six benchmarks; smaller models beat GPT-4o on some tasks at 4.55% of its inference cost (reported). Supports the cost-versus-pass-rate verdict logic.

### Reward overoptimisation (limits of metrics)
Link: https://arxiv.org/abs/2210.10760 (V-abs; Gao, Schulman, Hilton). An imperfect proxy reward, pushed too hard, lowers the gold-standard score (Goodhart's law); the effect follows smooth functional forms. Direct support for principle 7: search power raises the stakes of the metric being a proxy. Borrow: hold a secondary check the optimiser never sees (a held-out case set), recorded as a validity arm.

## 5. Routing, selection and experiments

### RouteLLM
Link: https://arxiv.org/abs/2406.18665 (V-abs; Ong et al., v4 February 2025). Router models trained on human preference data choose a stronger or weaker LLM per query; cost cut by over half in some cases without quality loss (reported); routers keep working when the model pair is swapped.
### Not Diamond
Link: https://www.notdiamond.ai/ (V-page). Commercial router; routing by predicted quality, prompt adaptation, custom routers trained on a customer's evals. Figures on the page (about 5% accuracy gain, about 20% cost saving, projected annual saving) are vendor claims, unverified. Martian (another router vendor named in the brief) was not fetched: NV.
Shares: automatic selection by metric. Differs: selection per request versus ESOI's per solution; shows that "best" can vary by input, the first test in "Whether best differs" at https://github.com/JoshuaMathias/evolvable-structure/blob/main/docs/explanation/when-to-create-a-sub-intent.md. Borrow: a router as a fourth selection mode alongside always-the-winner, for solutions where split tests show the winner varies.

### Feature toggles (Fowler)
Link: https://martinfowler.com/articles/feature-toggles.html (V-page). Release, experiment, ops and permissioning toggles; experiment toggles route users to cohorts and "needs to remain in place with the same configuration long enough to generate statistically significant results". Borrow: do not change an implementation's configuration mid-measurement; kill-switch (ops toggle) as the safe fallback for a selected implementation that regresses.
Bandits and A/B: not researched beyond this page; no primary source consulted for multi-armed bandit selection of prompts (NV, gap).

## 6. Oversight and governance

### NIST AI Risk Management Framework
Links: https://www.nist.gov/itl/ai-risk-management-framework (V-page: released 26 January 2023; Generative AI Profile NIST-AI-600-1 released 26 July 2024; under revision per the White House AI Action Plan) and https://airc.nist.gov/airmf-resources/airmf/5-sec-core/ (V-page). The full PDF (nist.ai.100-1.pdf) could not be read as text, so the subcategory quotes come from the web Core page. Functions: Govern (cross-cutting), Map, Measure, Manage. Quotes: "Processes for human oversight are defined, assessed, and documented" (Map 3.5); "The risks or trustworthiness characteristics that will not – or cannot – be measured are properly documented" (Measure 1.1); "independent assessors are involved in regular assessments and updates" (Measure 1.3); "AI systems should be tested before their deployment and regularly while in operation."
Shares: oversight as defined, documented process; measurement as continuing, not once.
Differs: risk-oriented, organisation-level; no alternatives or selection. Borrow: record what a metric cannot measure (a "not measured" field on each Metric); independent assessment of the metric itself.

### Scalable oversight, weak-to-strong, Constitutional AI
- Bowman et al., "Measuring Progress on Scalable Oversight": https://arxiv.org/abs/2211.03540 (V-abs). People assisted by an imperfect model through a chat interface outperformed the model alone and themselves unaided on MMLU and time-limited QuALITY.
- Burns et al., "Weak-to-Strong Generalization": https://arxiv.org/abs/2312.09390 (V-abs). Strong models fine-tuned on weak labels usually beat their supervisors but fall short of full capability; an auxiliary confidence loss helps.
- Bai et al., "Constitutional AI": https://arxiv.org/abs/2212.08073 (V-abs). Humans supply only a short list of principles; AI critiques, revises and judges (RLAIF).
- Mitchell, Ghosh, Luccioni, Pistilli, "Fully Autonomous AI Agents Should Not be Developed": https://arxiv.org/abs/2502.02649 (V-abs). "risks to people increase with the autonomy of a system."
Relevance: all put human attention at principles and measurement, which supports principle 4's "humans need only review metrics, not implementations (but they can still add value to implementations)". The weak-to-strong and scalable-oversight results are evidence that weaker evaluators can supervise stronger ones imperfectly, which supports ESOI's keeping humans on ideals and metrics while also recording that the supervision is limited (principle 7). Constitutional AI is the closest to "short human-written principles steer automated improvement", though it trains a model, not a repository. They do not support dropping implementation review for risky work; Mitchell et al. argue for caution as autonomy rises, a counterweight ESOI states as "they can still add value".
Human-in-the-loop versus on-the-loop: no single primary source was consulted that defines the terms; the page uses them only loosely (NV).

## What could not be verified or was not done
- DSPy docs pages on signatures and optimizers (redirect stubs only); OpenAI Evals page (403); OpenAI "Practices for governing agentic AI systems" (403); NIST AI 100-1 PDF (binary, not readable); Martian router; Kiro EARS notation; bandit or A/B selection of prompts; any primary definition of human-in-the-loop versus on-the-loop.
- Fetch results are summaries from a small model, not raw page text; quotes should be rechecked against the pages before external use.
- The claim that no existing framework combines intent records, rival implementations, metric-selected use, and an evolving structure is not proven; the search found none, within the limits above.
- Payne's stack carries inconsistent version labels and a not-production-tested caveat.

## Most useful borrowable ideas (ranked)
1. Archive of past alternatives kept as stepping stones (DGM, ADAS, OpenEvolve): losers and old versions help later search and past results stay comparable.
2. Pareto frontier selection (GEPA) when ideals conflict, instead of one number.
3. Capability-to-regression graduation and saturation retirement (Anthropic evals guide): a metric lifecycle that ESOI's eval versus invariant split does not yet name.
4. A "working signal" and a "not measured" field on records (Payne, NIST): observable test per layer and an honest list of what the metric cannot see.
5. Routing as a selection mode, with the rule to freeze configuration during measurement (RouteLLM, toggles): for solutions where split tests show the winner varies by input.
