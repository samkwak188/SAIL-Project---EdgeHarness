
**Router (the manager).** Classifies each incoming task and dispatches it. Known, recurring task type → cheap specialist. Novel, open-ended, or low-confidence → escalate to the generalist. The router's accuracy caps the whole system, so it is the primary design focus.

* **Specialist tier (the employees).** One base model with hot-swappable LoRA adapters — each adapter is a cheap fine-tune for a specific recurring task. Fast and cheap. This is where fine-tuning's strength is captured *inside* the system rather than competing with it.
* **Generalist tier (the senior partner).** The ensemble-plus-judge: several mid-sized open-weight models generate diverse candidates, a trained judge selects the best. Expensive, reserved for the hard tail. Over time it can also generate training data to mint new specialist adapters — described here as future work, not built in the six weeks. (see [ensemble.md](http://ensemble.md) for more details on the ensembling)

**Training the Router:**

**Training the Specialists:**

