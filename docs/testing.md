
Measures:

- Time to compute

- Accuracy threshold
	local output within X% of cloud baseline accuracy,
	for figures we could include the outputs it produced for both local v.s. cloud models.
- Latency threshold
	local output within X% of cloud baseline latency (total time it took)

**- Cost to compute**
**local output cost per task (compute cost, we could compute it against like a virtual server with specific RAM specifications)**
**v.s. Cloud baseline cost per task (we could calculate it off input/cached/output tokens)**
[**github.com/AgentOps-AI/tokencost**](http://github.com/AgentOps-AI/tokencost)

**- Sample size**
**we should set the number of times to run the task, before like an accuracy/latency/cost number is set, because each run the usage/duration varies**

Potential AI Integration we have mentioned - Admin, Documents, Customer Questions, Scheduling, Internal Information,

LegalBench - standard legal-reasoning benchmark suite - covers issue-spotting, rule-application, many sub-tasks under sub-categories
<!-- idk if this is actually necessary because this is like actual legal level stuff going on -->

CUAD (Contract Understanding Atticus Dataset @ Huggingface) - 500 contracts labeled for clause extraction… so we could see if it handles the clause extraction task correctly

hazyresearch.stanford.edu/legalbench/

**Script specs:**

The script abstracts away the exact API details of its local model (implementation details are not in the judge nor get response functions)

We also want judging to be extensible from Local vs. Cloud, but also Local (no ensemble) vs. Local (with ensemble) and such.

At the level of testing, any implementation details of a model are abstracted away into simply input (prompt / query) and output (the models or system of models response)

Other scripts deal with the implementation

**Judge Script:** 

Inputs: 

* Prompt / question (or a .csv or .parquet or whatever is most efficient with a list of questions),  
*  list of model references (ie. list of models to be ranked against, in our case usually local vs. cloud)  
* Judge mode (see below)

The questions optionally come with pre-provided answers. If they don’t have one, the judge must supply one **BUT** this is heavily advised against, all questions should have answers in a Question-Answer data format.

ANSWER can be rubric based or just say a number. So there are two “answer types” rubric, and 

It is in this case the judges job to weigh the success of the models.

There are a few simple modes by which the judge can rank:

1. By Reasoning: The Judge looks at the model's entire chain of reasoning. But this might become more expensive so except for problems where Successful reasoning doesn’t correlate strongly with correct final answer, this should be avoided. Additionally, business tasks generally care more about bottom lines, not intermediate steps.  
2. By answer: The judge only sees the final answer and ranks by that. We can imagine if the answer is 10 and a model provides a 9, the judge might rank highly in this case.  
3. Mixed: Both the final answer and by reasoning are considered and weighed.  
4. Deterministic: Answer correctness has no element of interpretation. In these types of problems, we should not deploy the judge.

Output: Each models scored labeled in dict format

<!-- consider this my first ideas and thoughts on testing. We want to research more into testing methodologies for maximum success. -->

<!-- I haven't yet considered how this formulation works with harnessed models with tool calling, right now this assumes an input->output flow of LLMs, which might not be quite what we need it to do. -->

