---
source: https://people.csail.mit.edu/asolar/SynthesisCourse/2025/Assignment4.htm
original_file: Assignment4.htm
---

Assignment 4

# Introduction to Program Synthesis

© Armando Solar-Lezama. 2018. All rights reserved.

[Lecture 1](Assignment4.md#about) [Lecture 2](Assignment4.md#services) [Lecture 3](Assignment4.md#clients) [Lecture 4](Assignment4.md#contact)

# Assignment 4

Submission Instructions This assignment is due at 5pm on the date indicated in the [ class calendar](index.md). See the note at the end of this document for instructions on how to submit your code.

Collaboration: You are allowed to collaborate with one other person for this assignment, but each of you is responsible for submitting your own solution. If you do collaborate with someone else, make sure to name your collaborator in your submission (in the PDF of Problem 1).

If you have any questions, please ask!

## Problem 1 (50 pts + 20 pts optional extension)

For the first problem of this assignment, you will gain experience with MCTS and using program synthesis to automatically prove theorems.

Begin by downloading the starter code for the assignment [here](pset4-mcts.tar.gz). This directory contains a theorem proving environment defined in `env/`, as well as the beginnings of a `main.py` file that you will use to run the MCTS algorithm. It also contains a `theorems.txt` file. This contains a list of 69 different theorems, along with their proofs, written in the syntax of the theorem prover defined by the code in `env/`. Your job is to use MCTS to build an agent which is capable of proving (some of) these theorems. To help build intuition for why each part of MCTS is necessary, you will be required to implement it in 5 stages (parts a-e). These should be implemented in five separate files, named `q1a.py`, `q1b.py`, `q1c.py`, `q1d.py`, and `q1e.py`. The main script will automatically load the agent defined in the file you request (see the `main.py` file for details).

In addition to submitting your code, please submit a PDF file q1.pdf containing the results (and some brief discussion) of your experiments. This report must contain:

- A section for each part `a-e` briefly describing your implementation of that part in your own words. These does not need to be elaborate, and will only be used as a backup to help us assess your understanding. If the results of your experiments do not look like what we expected or we find your implementation to be incorrect, we may use these to assign you partial marks for your efforts.

- A section titled "Experiments" containing:

- A single table or bar plot showing the results in terms of mean number of theorems proved. You should have a total of ten (10) rows/bars; one for each item in the cross product between parts `a-e` (of which there are five) and max_attempts $\in \{10, 100\}$ (of which there are two). The rows should be ordered by part (a-e), and the columns should be ordered by max_attempts. Note that your agent will necessarily be stochastic, you will have to run it multiple times to get a good estimate of its performance; we recommend running it at least 50 times (that is, with 50 different seeds) for each part of the assignment, and displaying your results with a 95% confidence interval on the mean.

- A single paragraph discussing the findings. In particular, discuss how the number of theorems proved changes as you make the algorithm more elaborate, and whether any parts of the results surprised you or otherwise did not match your expectation.

- A section titled "Extension" if you attempted the Extension question, detailing the approach you took and what your findings were.

Environment Overview: The theorem proving environment (`env/`) implements a simplified propositional logic theorem prover. It consists of several key components:

- ProofState (`state.py`): Represents the current state of a proof with a list of goals to prove and a context of available hypotheses. A proof is complete when all goals are satisfied.

- Actions (`actions.py`): Defines the available proof tactics including basic tactics like `exact` (directly apply a hypothesis), `apply` (apply an implication), and structural tactics like `split` (for conjunctions), `left`/`right` (for disjunctions).

- Language (`language.py`): Defines propositional logic constructs including variables (`Var`), conjunctions (`And`), implications (`Implies`), disjunctions (`Or`), and falsehood (`PropFalse`).

- Interaction (`interaction.py`): Provides the `step` function that applies actions to states, returning a new state or `None` if the action is invalid.

- Tactics (`tactics.py`): Implements the actual proof tactics that manipulate the proof state by adding or removing goals and updating the context.

The environment comes with 69 theorems of varying difficulty in `theorems.txt`, ranging from simple 1-step proofs to complex multi-step proofs involving conjunctions, disjunctions, and nested implications. Important: Do not modify the files in `env/`! If you find a bug in the environment, please report it to us on Canvas so we can fix it for everyone instead.

Installation: You will need Python >= 3.12 due to the type annotations used in the `env/` code. You will not need any other dependencies, as the code in `env/` is self-contained. In your implementations, you may use all of Python's standard library, but you should not use any third-party libraries (e.g., NumPy, Pandas, etc.) unless you are doing the Extension question.

Grading: Each part `a-e` will be worth 8 points, for a total of 40 points. The remaining 10 points will be awarded based on the quality of your report.

###  Part a)

To begin with, you will implement a random agent with a naive state representation, which will serve as a baseline for the more sophisticated agents you will implement in the following parts. For each theorem, the agent will simply carry out `args.max_attempts` different rollouts (aka simulations), each one of which is carried out by repeatedly picking an action uniformly at random from those defined in `env.actions -> ACTION_SPACE` and then using the `step` function defined in `env/interaction.py` to carry out the action. This is continued until the theorem has successfully been proven (`state.is_complete` is `True`), or an error occurs (e.g. the action is invalid, and `step` returns `None`). As to the value of the state, the agent should simply return +1 if the rollout was successful (i.e., a proof was found), and 0 otherwise. Implement the agent in `q1a.py` (as well as updating `main.py` accordingly). It must expose a class `Agent` with (at least) the method `rollout(self, state: state.ProofState) -> tuple[state.Value, interaction.Trajectory]`, which your `main.py` script will call to carry out `args.max_attempts` rollouts. The first return value should be the value of the state (i.e., +1 if a proof was found, 0 otherwise), and the second return value should be the trajectory of actions taken to reach the final state during the rollout (this can be useful for debugging purposes, but note that the rollout trajectory is not included when updating the visit counts in MCTS, so it is not strictly necessary to return it).
You can run your agent with

`````
python main.py --agent 1a --max_attempts=[max_attempts]
`````

Expected behaviour: This should only prove a few theorems, depending on the number of rollouts performed.

Hint: We're going to continue building up each part of the MCTS algorithm, so to make your life easier, you should probably define a base agent class to hold the state-action visit counts and $Q(s, a)$ values as well as some no-op implementations of the different MCTS functions. Then, you can simply override these functions in each part of the assignment, and your `main.py` script can remain much simpler.

###  Part b)

Having established a naive baseline, we will now start implementing a more sophisticated agent based on MCTS. For this part, you will implement the `select` and `expand` steps of MCTS, as described in lecture. Your `main.py` script should therefore first call the `select` function, which will select a state to expand, then call the `expand` function to expand that state. Once the state has been expanded, carry out a rollout from the newly expanded state using the same random rollout as in part a). Finally, whether or not the rollout lead to a successful proof, the state counts should be updated to reflect the result of the rollout.

Note that the `select` function depends on $Q(s, a)$, which we haven't defined yet. For this part, just set $Q(s, a) = 0$ for all states $s$ and actions $a$; we will define it properly in part c). Futhermore, set the UCB constant $C$ to $\sqrt{2}$. This value has theoretical backing for the type of problem we are solving (multi-armed bandits), but we won't have bandwidth to talk more about why in this class; you will have to take a proper reinforcement learning class instead!

For reasons that will become apparent later, you should make your `Q` table to be of type `state.AbstractState -> actions.Action -> float`. Your state-action visit counts should similarly be of type `state.AbstractState -> actions.Action -> int`. The `state.AbstractState` type is defined in `env/state.py`, and is meant to represent the agent's view of the current state of the theorem prover (which is a `state.ProofState`). For now, just use `str(state)` as your state representation; we will return to this when we explore the impact of state abstractions in parts `d-e`. Implement the agent in `q1b.py` (as well as updating `main.py` accordingly). It must expose an `Agent` class with (again, at least) two methods:

- `select(self, initial_state: state.ProofState) -> tuple[state.ProofState | None, interaction.Trajectory]`. The first return value should be the state selected for expansion (or `None` if search ended up in an invalid state), or `None` if no state was selected (e.g., if the initial state is already complete). The second return value should be the trajectory of actions taken to reach the selected state. Unlike the trajectory from the rollouts, this trajectory will actually be used to update the visit counts in MCTS, so it is important that it is correct.

- `expand(self, state_to_expand: state.ProofState) -> tuple[state.ProofState | None, actions.Action]`. This should simply return the result of expanding the state with a fresh action (which might be `None` if the action was actually invalid at this point), as well as the chosen action itself.

You can run your agent with

`````
python main.py --agent parts/b --max_attempts=[max_attempts]
`````

Expected behaviour: You may see some very slight improvement over the naive agent from part a), but it will still be quite poor, since there is no learning taking place yet.

###  Part c)

Part b) improves upon the naive agent by using the UCB criterion (ie., the `search(s)` function from the lecture) to select which part of the search space to pursue next. However, it still uses a naive rollout strategy, and no "learning" is actually taking place. In this part, you will remedy this by making two changes:

- Implementing the backprop function to "learn" (estimate) $Q(s, a)$. For this, simply follow the formula discussed in the lecture.

- Use on-policy rollouts, where the probability of selecting an action depends on the current estimate of $Q(s, a)$. Specifically, we will use an epsilon-greeedy policy: with probability $\epsilon$ (which you can set to 0.1), select an action uniformly at random, and with probability $1 - \epsilon$, select the action with the highest $Q(s, a)$ value. If there are multiple actions with the same $Q(s, a)$ value, select one of them uniformly at random.

As you have probably guessed by now, you should expose an `Agent` class in `q1c.py` with at least the following methods:

- `backprop(self, value: state.Value, trajectory: Trajectory)`. (No return needed unless you do not use a stateful/class-based approach to keep track of the $Q(s, a)$ and $N(s, a)$ tables.)

- `rollout`: same type signature as in part a), but now the rollout should use the epsilon-greedy policy to select actions.
Note that depending on how you are structuring your code, you may need to reimplement the `select` and `expand` methods from part b) to use the $Q(s, a)$ and $N(s, a)$ table that you are now updating during backprop.
You can run your agent with

`````
python main.py --agent parts/c --max_attempts=[max_attempts]
`````

Expected behaviour: This should roughly double the number of theorems proved compared to part b), but will still be far from perfect.

###  Part d)

We have now implemented the basic MCTS algorithm, but it is still not very effective. This is because we are using a very naive state representation, which makes it difficult for the agent to learn anything useful. Consider the following two theorems:  theorem level1 (hq: p) : p := exact hq theorem level2 (hp: p, hpq: p -> q) : q := apply hpq exact hp  Once the agent has gone down the path of `apply hpq` in the second theorem, the remaining proof is the same as in the first theorem: `exact hp`. We would therefore like the agent to recognize this, and avoid having to re-learn the same proof over and over again. However, with our current state representation, this cannot actually happen, because the proof state is different for each theorem: in the second case, even though the only goal remaining is `p`, the context of the proof also contains `hpq: p -> q`, thus preventing the agent from recognizing that the goal is the same as in the first theorem. Over this part and the next, you experiment with different state representations to see how they affect the performance of the agent. Note that the difficulty of obtaining the "best" state representation is part of the reason why neural-network-based MCTS agents are so popular: they can learn a good state representation automatically, rather than having to rely on a human to design it. However, that is beyond the scope of this part of the assignment, so we will instead explore a few simple state representations that you can implement by hand. If you are interested, you can explore a neural-network-based MCTS agent in the Extension question.

For this part, your goal is to implement a state representation such that your agent from Part c) does worse than the random agent from Part a). Yes, you read that right: the goal is to make the agent worse than the random agent. This is to help you understand the importance of state representations in MCTS (and RL), and how a poor state representation can actually make a learning agent worse than even a naive baseline!

Implement the agent in `q1d.py` (as well as updating `main.py` accordingly, if needed). It must expose an `Agent` class with the same methods as in part c), as well as a method `abstract(self, proof_state: state.ProofState) -> state.AbstractState` that takes a `state.ProofState` and returns an `state.AbstractState`, which you should use as the state representation for the agent when selecting actions and updating the $Q(s, a)$ and $N(s, a)$ tables.
You can run your agent with

`````
python main.py --agent parts/d --max_attempts=[max_attempts]
`````

Expected behaviour: Your should be able to come up with state representation that leads to fewer theorems being proved than the random agent from part a).

Hint: Learning will make the agent worse than the random agent if it "confuses" states, thus causing it to "learn" to apply actions in the wrong state. Is there a trivial way to maximize this confusion?

###  Part e)

Your final task is to implement a more useful state representation that allows the agent to perform even better than its implementation in Part c). Implement this in `q1e.py` (as well as updating `main.py` accordingly, if needed, as always), with the same interface as in Part d).
You can run your agent with

`````
python main.py --agent parts/e --max_attempts=[max_attempts]
`````

Expected behaviour: Our reference implementation of this part was able to prove 15-20 theorems with 10 rollouts, and about 45-50 theorems with 100 rollouts.

Hint: Think about which parts of the ProofState are actually relevant to the agent's decision-making process at each step.

### Extension (Optional)

For those of you who are interested in using machine learning for theorem proving, you can optionally consider the following extension questions. As always, this is not required; you can get 100/100 marks on this pset without doing this extension. The 20 marks that are up for grabs here will roll over to future assignments, but the main reason to do is to gain experience with using machine learning for theorem proving, which is a very active area of research. If you do choose to do this extension, please submit your code in a directory called `extension/` inside the `problem1/` directory.

In increasing order of technical difficulty, the extension questions are:

- Option 1: Since we are tackling the theorems in order, the ordering (and nature) of the theorems in `theorems.txt` is actually quite important. For example, if we remove the easier theorems, the agent will have a much harder time learning to prove the harder ones. Try to come up with a better ordering of the theorems in `theorems.txt` that allows the agent to learn more effectively, or even considering adding new theorems to the list. Can you come up with a theorem curriculum that allows the agent to learn to prove all the theorems in `theorems.txt`?

- Option 2: In this pset we have used a custom, hand-rolled theorem prover. Open-source environments such as LeanDojo expose similar APIs to real-world theorem provers (in this case Lean). Can you replicate (part of) your findings in such an environment? Are there challenges there that did not come up in this pset?

- Option 3: Chances are that even with your carefully tuned state representation in Part e), your agent failed to prove all of the theorems. Can you train a neural-network-based policy instead, as in AlphaGo? Data efficiency will be a challenge; how can you obtain a training set that is extensive enough to learn the representation?

## Part 2 (50 pts)

For this part you will be working in Python, using the CVC5 library, which implements the Sygus solver. For an example of how to use the CVC5 library, see the file `q2/example.py`. Full documentation can be found [here](https://cvc5.github.io/docs/cvc5-1.0.2/api/python/base/python.html). Note that since we are using the Sygus solver, you must use the Base Python API, not the Pythonic API.

The goal of the second problem will be to synthesize invariants necessary to prove that a piece of code is correct. We will be working in the context of a very simple language involving variables, simple arithmetic operations, and a set of simple commands (if, while, assignment and sequential composition). You will implement this in two parts, first, you will generate the verification condition as an AST using the same AST nodes provided to you for representing the program, and then you will generate CVC5 code and solve from this AST.
a) VC as an AST: For this part, you may need to introduce additional Expr nodes in order to represent the unknown invariants and to indicate the variables that may be used by this. Other than that, this should be a relatively straightforward implementation of verification condition generation. To check your work, ensure that

`````
python q2/q2.py 2a
`````

runs without errors.

b) Verification using CVC5: For the second part, you will need to implement two functions. First, on each Expr node, implement `to_cvc5` which takes an Expr and returns a CVC5 expression. The [full list of Kinds](https://cvc5.github.io/docs/cvc5-1.0.2/api/python/base/kind.html) is useful for determining what functions are available. Also look at `q2/example.py` for examples of how to use the CVC5 library. You will need to implement this for any Expr nodes you added in part a. Note that `variables` is a dictionary mapping variable names to CVC5 variables, and `invariants` is a dictionary mapping Expr nodes to CVC5 functions, like `min/max` from the example. Second, implement `solve`. In this function you will need to set up `variables` and `invariants` and then call `to_cvc5` on the assumption and VC. To check your work, ensure that

`````
python q2/q2.py 2b
`````

runs without errors.

c) Test cases: You need to submit five test cases for which your system can generate interesting invariants. Place these in example_N for N from 2-6. You can run your code on these test cases by running

`````
python q2/q2.py 2c
`````

Note: the invariants you generate should be relatively shallow when thought of as trees, otherwise the solver won't find a solution quickly. For example, the following invariant does not work well:

`````
x >= 0 && y >= 0 && 3x + 2y >= 0
`````

## Submission

Submit your code on Canvas as a .tar.gz file containing:

- `q1/`

- `q1.pdf`

- `main.py`

- `q1a.py`

- `q1b.py`

- `q1c.py`

- `q1d.py`

- `q1e.py`

- `extension/`: Any additional code you wrote for the extension question, if applicable.

- `q2/`

- `q2.py`
