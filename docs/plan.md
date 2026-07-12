
First Target Audience: DeWitt LLP Law Firm
Current AI Integration - Working with another firm to integrate AI into their accounting workflow

> to show that we are capable of doing other workflow automation - we could potentially try out basic accounting tasks with local models v.s. cloud models (Opus 4.8) to prove that the accuracy and time taken does not differ by too much

Important Things to measure: How long each iteration takes, How accurate the output is (by comparing the optimal answer to the output of each LLM)

**~~Six~~ -Four week scope — the honest bar**

By the end of six weeks we target a working prototype, not a finished product. Concretely:

* A working **router** that distinguishes 2–3 known task types from an 'everything else' bucket, with a confidence-based escalation rule.
* **2–3 specialist adapters** for the known task types (each a 1–2 day fine-tune). (Maybe only 1-2 because of new time constraints)
* The **ensemble-plus-judge generalist** as the fallback path.
* A measured result: across a **basket of (?) tasks**, the routed local system matches or approaches a frontier (GPT/Claude) baseline on quality, while being cheaper than running the ensemble on everything — all running on local hardware.

<!-- ok all good 3:o) -->

**Local model base:**

We currently plan to use Groq as a base model *(although this is subject to change)*

**Routing:**

A business may have many different tasks they want local AI to deal with, for this reason we plan to add routing features.

For specifics on how we handle routing, see *routing.md*

**Testing:**

We are going to test our model's suggestions, answers, and other outputs against the outputs of traditional cloud models (Claude, ChatGPT, etc.)

For our purposes we have chosen to use the cloud model *(ex. Claude)* because it *(ex. represents the cutting edge, cheapest, whatever).* Although our script is extensible to any other model for comparison.

For more information on Testing, including documentation on the script, go to [*testing.md*](http://testing.md) *(it should link to another part of the repo)*

The importance of testing is to ensure our local solution provides the same level of accuracy companies can expect from cloud models.

**Key Concerns:**

An ensemble of models could get very computationally heavyweight. This is a concern. We might want to look into deepseeks innovations on local models,
or perhaps fine tuning the specialists can reduce computation.
<!-- I don't believe adapters can improve computation speed outside of increasing tokens/task efficiency, though not sure -->

One of us needs to figure out the Center for Computer resources interface.

