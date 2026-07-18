---
source: https://people.csail.mit.edu/asolar/SynthesisCourse/2025/Assignment2.htm
original_file: Assignment2.htm
---

Assignment 2

# Introduction to Program Synthesis

© Armando Solar-Lezama. 2018. All rights reserved.

[Lecture 1](Assignment2.md#about) [Lecture 2](Assignment2.md#services) [Lecture 3](Assignment2.md#clients) [Lecture 4](Assignment2.md#contact)

# Assignment 2

Submission Instructions This assignment is due at 5pm on the date indicated in the [ class calendar](index.md). To submit your code, put question1a.sk and question1b.sk in the q1/ directory and compress the whole parent directory containing q1/ and q2-3/ into a .tar.gz file, then submit it through the Canvas assignment.

Collaboration policy You are allowed to consult with at most one other student while working on the pset, but every student is responsible for writing their own code and submitting their own work. If you do consult with another student, you should explicitly acknowledge them in your submission (you can do that in a comment in `question1a.sk`).

## Problem 1 (30 pts)

For this problem, you will be encoding an arithmetic language in Sketch to synthesize expressions matching input output examples. You should download the latest version of sketch from [here](http://people.csail.mit.edu/asolar/sketch-1.7.6.tar.gz). Note: unless you run into issues, do not follow the build instructions. Just unzip the file, and then run the binary located at sketch-frontend/sketch. On some operating systems (e.g. one TA's M1 Mac) you may need to follow the build instructions. To test that your installation is working, you may find it useful to ensure that the first example sketch (`doubleSketch`) from the manual works.
Consider the following simple arithmetic language:
Int := | n.................................// numeric constant | x.................................// variable | Plus(int, int):int................// addition | Times(int, int):int...............// multiplication | ITE(bool, int, int):int...........// if-then-else Bool := | false.............................// constant false | true..............................// constant true | Lt(int, int):bool.................// less than | Not(bool):bool....................// boolean negation | And(bool, bool):bool..............// boolean conjunction

### Problem 1.a

Encode the arithmetic grammar from above as a generator in Sketch, using it to synthesize functions solving the following examples:  x=5, y=5, out=15; x=8, y=3, out=14; x=1234, y=227, out=1688;  And  x=10, y=7, out=17 x=4, y=7, out=-7 x=10, y=3, out=13 x=1, y=-7, out=-6 x=1, y=8, out=-8  Starter code for this problem can be found [here](question1.sk.md). You will find the [sketch language reference](http://people.csail.mit.edu/asolar/manual.pdf) useful. Submit your code as `question1a.sk`.

### Problem 1.b

In a copy of the file, add the following constraints:

- Multiplications can only occur between variables and constants or between two variables

- Comparisons cannot include any arithmetic, only variables and constants

Submit your code as `question1b.sk`.

## Problem 2 (40 pts)

Top-down searches ([Lecture 4](Lecture4.md)) are widely used technique in program synthesis as they are simple and general, not requiring the context-independent equivalence property relied on by bottom-up approaches. Top-down enumeration exhaustively explores a space of programs in a grammar by repeatedly expanding holes in the current partially-constructed program using production rules from the grammar. A key part of efficient top-down enumeration is the ability to perform these expansions by mutating the program in-place, rather than making a copy of the entire program at each step. When the search hits a dead end (e.g. a size limit is reached, or an incorrect program is found) we require the ability to backtrack by undoing the expansions ("unexpanding") in-place. This problem will guide you through implementing expansion and unexpansion, then using them to implement the overall top-down search algorithm.
Skeleton code for this problem can be found [here](pset2.tar.gz).
First, move to the `q2-3/` directory and run the following command to install the necessary packages:
julia --project -e 'using Pkg; Pkg.instantiate()'  Then run the following command to make sure everything is set up properly:  julia --project test/internal.jl  Notes:

- You can see some example graphics programs in the language [here](pset2_content/pset2_viewer.md).

- The code you write will not be specific to the graphics domain, but the tests will run in the graphics domain so it may be helpful to take a look at the grammar and associated comments in `src/drawing_domain/drawing_grammar.jl`.

- Don't edit the type signatures of the functions you implement.

### Problem 2.a

First, write implementations of the following functions in `src/program_search/expansion.jl`. Refer to the definitions and docstrings of the expression type `struct Exp` and the production rule type `struct Production` to understand their structure.

-  `expand_inner`: Applies a production to a hole to turn it into an expression with new holes as arguments. This should mutate the hole expression in place to have a new `.head`, `.data`, and `.args`.

-  `unexpand_inner`: Undo all the effects of `expand_inner`, replacing the expression with a hole of the given type.

You can test your implementation with the following command:  julia --project test/q2a.jl

### Problem 2.b

Implement `expand` and `unexpand` in `src/program_search/top_down.jl`. These functions should call `expand_inner` and `unexpand_inner`, and modifying the search state (`struct TopDownSearch`) fields `.e`, `.weight`, and `.holes` appropriately. See the definitions of `struct TopDownSearch` and `struct SubExp` for the expected structure.

- `expand()` can assume that the hole to be expanded has already been popped from `.holes`, so it shouldn't do that.

- Since `unexpand()` is the inverse of `expand()`, it also shouldn't push the unexpanded hole back onto `.holes`.

- The testing code assumes that new holes are pushed to the end of `.holes` and are ordered from left to right

You can test your implementation with the following command:  julia --project test/q2b.jl

### Problem 2.c

Implement `top_down_search` in `src/program_search/top_down.jl`. This function should perform a depth-first top-down enumerative search, and will call `expand` and `unexpand`. The search should be bounded in a few ways, configured by `search.config` (see `struct TopDownConfig`).

- It won't perform an expansion if it would cause the weight to exceed `config.max_weight`.

- It won't perform an expansion if the number of expansions performed (`search.result.stats.expansions`) exceeds `config.max_expansions`.

- It only attempts to evaluate a completed program if the weight of the program is greater than or equal to `config.min_weight`.

The last condition might seem odd, but it's relevant because your top-down search code will be executed by the testing code within a larger iterative deepening search, which will first attempt to find all programs in the weight range [0, 1.0], then [1.0, 2.0], etc. The last condition avoids wasting effort re-evaluating solutions that were encountered in earlier iterations of the iterative deepening search.
The pseudocode for the `top_down_search` function you will implement is given below:

- Pop a hole from the end of `search.holes`.

- For each production in the grammar:

- If the production's return type does not match the hole's type, skip it.

- If expanding to it would cause the weight to exceed the max weight, skip it.

- If the number of expansions so far is greater than the maximum number of expansions allowed, skip it.

- Expand the hole with the production.

- If there are no more remaining holes to expand AND the weight is greater than or equal to the min weight, evaluate the solution with `evaluate_solution(search)`.

- If there are remaining holes to expand, recursively call `top_down_search(search)`.

- Unexpand the hole.

- Push the hole back onto `search.holes`.

You can test your implementation with the following command:
julia --project test/q2c.jl

### Problem 2.d

In this part we'll explore the value of types in constraining the size of the search space.
Modify `top_down_search` so that if `config.disable_types` is true, it doesn't check that the production type matches the hole type.
To measure the size of the search space more easily, we've created a test that doesn't actually execute programs, and just reports the number of expansions and number of complete programs encountered at each layer of the iterative deepening search. Run it with the following command:  julia --project test/q2d.jl  This will run the search with and without type-based pruning - you should get a dramatic difference in the number of expansions and completions.

## Problem 3 (30 pts)

Note on dependencies with Problem 2: Part 3(b-d) rely on having finished 2(b); part 3(c) is similar to 2(c) so doing 2(c) first is recommended; and the ungraded final DreamCoder test at the end of Problem 3 relies on having finished 2(c).
This problem builds on the previous problem, exploring component discovery ([Lecture 9](Lecture9.md)) in the same graphics domain, which is inspired by a domain from the DreamCoder paper. In Part (a), you'll be using an off-the-shelf component discovery tool (Stitch) to discover components in the graphics domain. Stitch approaches component discovery through a top-down search over the space of components, made efficient through a branch-and-bound strategy. In Part (b-d), you'll be implementing a component discovery algorithm that incorporates some of the core ideas of Stitch.

### Problem 3.a

Install the Python bindings for Stitch from [here](https://stitch-bindings.readthedocs.io/en/stable/).
Modify `q3a.py` to call Stitch on the ground truth programs in `data/graphics.json`. Run Stitch for 3 iterations with a max arity of 3. Print out the 3 components (abstractions) along with the rewritten programs. Include the output of your code in the placeholder comment at the bottom of the file.

What do you think each of the components do? Add a comment very briefly explaining each component. It can be helpful to look at which rewritten programs the components are used in.

### Problem 3.b

As discussed in [Lecture 9](Lecture9.md), at each step of search Stitch expands a partial component with a production from the grammar. For example, we might expand the rightmost hole of `(+ ?int ?int)` with the production `(* ?int ?int)` to get `(+ ?int (* ?int ?int))`.
When expanding a hole with a production, the new partial component will match at a subset of the locations it matched at before. This subset property is critical to the efficiency of the search: to get our new set of matches after an expansion, we can simply filter the original set of matches to only keep the ones where the chosen production (`(* ?int ?int)`) appears at the expansion location.
Implement `subset_matches_to_production` in `component_search/branch_and_bound.jl`. This function performs the subsetting operation described above, setting `search.matches` to a (new) filtered list of matches - but doesn't mutate the input list of matches nor the original `search.matches`. A few points that may be helpful:

- The list of matches is a list of Exp objects corresponding to the top node that the component is matching at. Each of these Exp objects has its `.scratch` field populated with a `CorpusData` object which contains the production and total weight of the expression; you can access it through the `corpus_data(e::Exp)` function.

- You can assume all children and descendants of the matches similarly have `CorpusData` objects.

- You will likely need to use `get_descendant(e::Exp, zipper::Vector{Int})` to get the descendant of an expression at a given zipper.

- The tests will apply your implementations of `expand` and `unexpand` from Problem 2(b) to the `ComponentSearch` type (this likely doesn't require any changes on your part since the structs are similar).

You can test your implementation with the following command:  julia --project test/q3b.jl

### Problem 3.c

Implement `branch_and_bound` in `component_search/branch_and_bound.jl`. This is the main loop of the component search, and will be quite similar to the implementation of `top_down_search` from Problem 2(c). There are a few points at which it's noted that you must call a specific function - be sure to do so, as it's key to automatically incorporating some extensions later. The pseudocode is given below:

- Keep the original `search.matches` in a variable (to restore at the end).

- Pop a hole from the end of `search.holes`.

- For each production in `possible_productions(search)`: (note: you must call the provided `possible_productions` function)

- If `ill_typed_production(production, hole)` is true, skip it. (Note: you must call this function.)

- Subset the matches to the production (careful with which matches you use here!).

- If `prune_search(search)` is true, skip it (for now this is always false, pruning will be added in the next part).

- Expand the hole with the production using your existing implementation of `expand`.

- If there are no more remaining holes to expand, evaluate the component with `evaluate_component(search)`.

- If there are remaining holes to expand, recursively call `branch_and_bound(search)`.

- Unexpand the hole.

- Push the hole back onto `search.holes`.

- Set `search.matches` to the original matches.

You can test your implementation with the following command. It will only find components that don't use variables, so it will just find various large, common subtrees.  julia --project test/q3c-novars.jl  However, through `component_search/vars.jl`, we've added support for variables which should allow for some more interesting components. You shouldn't have to make any changes unless you run into issues. Run it with the following command:  julia --project test/q3c-vars.jl

### Problem 3.d

Implement the following functions in `component_search/branch_and_bound.jl`:

- `upper_bound`: As in lecture, simply take the sum of the total weights of the matches (Hint: use `corpus_data`).

- `prune_search`: Return true if this branch of the search should be pruned. Include the following checks:

- If the number of matches is less than 2, return true. This is just to avoid uninteresting components that appear in a single place.

- If the upper bound is less than or equal to the utility of the best component found so far (stored in `search.result`), return true.

- If `prune_useless_arg(search)` returns true, then return true. This function is implemented for you, and is an optimization of Stitch saying if an argument always takes the same value, then we can prune the component (because there exists a better component that doesn't have an argument at all and just includes the value in the body of the component).

- You don't need to implement it, but Stitch had one more form of pruning: if a component has two arguments but within each match location the two arguments are always the same as each other, then the component can be pruned (because it's better to just reuse the same argument twice).

You can see the effect of pruning even on the small set of graphics programs with the following command:  julia --project test/q3d-base.jl

### Problem 3.e (optional, ungraded)

There's no implementation in this section, just a few extra commands to try. The pruning from the previous part also allows us to scale up to the nuts-bolts domain used in the [Stitch paper](https://dl.acm.org/doi/10.1145/3571234) (originally from [](https://arxiv.org/abs/2205.05666)Wong et al. 2022). You can run this domain with the following command (note that this doesn't run the without-pruning version as that fails to terminate):  julia --project test/q3d-scaling.jl  Finally, equipped with a component discovery algorithm, we can recreate a simple version of the DreamCoder synthesis loop, alternating between component discovery to add new components to the grammar and synthesis to find new solutions to run component discovery on. You can run it with the following command:  julia --project test/q3d-dreamcoder.jl  If you have multiple cores, you can add a `julia -t [num_threads]` flag to the command to use multiple threads. You should see that the first 5 tasks are solved in the first iteration. A polygon drawing component is learned which is then used to solve tasks 7-8. From these, a chain of polygons component is learned. The discovery of the polygon component brings the search closer to solving the last few tasks which have to do with rotational symmetry, but the search as-is is not quite able to solve them.
You can use the following command to run all tests from Problems 2 and 3 (except for the dreamcoder test since it takes longer):
julia --project src/run_all_tests.jl
