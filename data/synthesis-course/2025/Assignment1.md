---
source: https://people.csail.mit.edu/asolar/SynthesisCourse/2025/Assignment1.htm
original_file: Assignment1.htm
---

Assignment 1

# Introduction to Program Synthesis

© Armando Solar-Lezama. 2025. All rights reserved.

[Lecture 1](Assignment1.md#about) [Lecture 2](Assignment1.md#services) [Lecture 3](Assignment1.md#clients) [Lecture 4](Assignment1.md#contact)

# Assignment 1

Submission Instructions This assignment is due at 5pm on the date indicated in the [ class calendar](index.md). The starter code for the assignment can be found [here](pset1.tar.gz). In order to submit your code, pack your `BottomUpEnumerator.jl`, `Question2.jl`, `question3a.js`, and `question3b.txt` files into a tar file and submit through Canvas (we will create a Canvas assignment as the deadline approaches).

Collaboration policy You are allowed to consult with at most one other student while working on the pset, but every student is responsible for writing their own code and submitting their own work. If you do consult with another student, you should explicitly acknowledge them in your submission (you can do that in a comment in `BottomUpEnumerator.jl`).

## Setup instructions

First, you should install julia using the instructions [here](https://julialang.org/downloads/). Then, install the packages you will need for this assignment by running the following commands in the julia REPL:  julia> import Pkg julia> Pkg.add("MLStyle") julia> Pkg.add("Images")  After you have done this you should be able to run the internal tests and see that they pass, as such:  $ julia test/runtests.jl internal Test Summary: | Pass Total internal | 1 1  If you run into issues, you can alternatively try installing the packages locally into the project environment by launching the julia REPL with `julia --project` to install the packages with the above instructions, and running the tests with `julia --project test/runtests.jl internal`

## Problem 1 (40 pts)

The goal of this assignment is for you to experiment with some of the bottom up inductive synthesis algorithm discussed in class. The code defining the language and interpreter is in the `src` directory, under `Combinata.jl` and `Interpreter.jl`. You should only modify the `BottomUpEnumerator.jl` file; you will submit only this file for Question 1. We have defined a simple language for the following expressions:  Coordinate := | Coordinate(int, int)................// a coordinate in the plane. Coordinates must be between 0 and MAX_COORD Shape := | Rect(Coordinate, Coordinate)........// a rectangle with the given lower left and top right coordinates | Triangle(Coordinate, Coordinate)....// the triangle represented by the bottom right half of the equivalent Rect | Circle(Coordinate, int).............// a circle with the given center and radius. Must have nonzero area | SUnion(Shape, Shape)................// the set-union of two shapes | SIntersection(Shape, Shape).........// the set-intersection of two shapes | Mirror(Shape).......................// the union of a shape with its mirror image across the line y=x  As part of the starter code for this project, we have included constructors for all the different AST nodes, as well as a basic interpreter `interpret()` that you can use to evaluate expressions in this language. Make sure to use `make_coord`, `make_rect`, `make_triangle`, and `make_circle` rather than calling the constructors directly. These functions will check that the coordinates are valid and throw an error if they are not. To see examples of how to render shapes for debugging, you can look at the `Render.jl` file, specifically the function `render_examples`.

### Problem 1a

As a starter task, implement the function `grow` in `BottomUpEnumerator.jl`. This function takes a list of shapes and returns a list of shapes containing

- All the shapes in the input list

- And all the shapes that can be obtained by applying `SUnion`, `SIntersection`, or `SMirror` once to shapes in the input list

You can test your implementation by running the following command on your command line:  $ julia test/runtests.jl question-1a

### Problem 1b

Your goal is now to implement a new the rest of the bottom up enumeration algorithm. Specifically, implement `elim_equivalents`, which takes a list of shapes and returns a list of shapes containing all the shapes in the input list, but with all equivalent shapes removed. Two shapes are equivalent if they have the same input/output behavior on the given points. The `Dict` feature in Julia will be useful for this task.
Then, implement `synthesize`, which takes a list of input/output pairs and returns a shape that matches the input/output pairs.
You can test your implementation by running the following command on your command line:
$ julia test/runtests.jl question-1b
Many of these tests might take several seconds, but not much longer. The entire question-1b suite takes around 20-90 seconds on our laptops. If your tests are taking much longer than this (> 5 minutes), you should consider revising your implementation.

Hint for the test `flipped_triangle`: make sure that the Context independent equivalence property holds for your implementation.

## Problem 2 (30 pts)

Consider the following grammar for a problem:  term:= last2Digits(x + ??) || last3Digits(x + ??) || last4Digits(x + ??) || last5Digits(x + ??) prog:= term ++ term ++ term ++ term  For example, the program `last2Digits(x + 3) ++ last3Digits(x + 537) ++ last4Digits(x + 82) ++ last5Digits(x + 87)` applied to 9928 should return 31465001010015 (31 ++ 465 ++ 0010 ++ 100015). The question marks ?? indicate unknown constants. You should assume the function operates only over the integers. Even though the space of potential expression is very large, the search space has a lot of structure. Our goal for this problem is to come up with a representation of the search space and a search strategy that exploits this structure and allows us to efficiently solve for a program in this space given a set of input/output pairs. In particular, the goal is to find a way to factor the search so it is possible to solve for the unknowns without having to search the exponentially large space.

Your goal is to implement a function with the interface below.  function structured(inputoutputs)  Where `inputoutputs` is a list of input output pairs (each input/output pair represented as a tuple of Int64, String). The function should return an AST for the synthesized program using the same format as `example_lkd`. The key requirement is that your function should execute in linear time with respect to the size of this input list. Your code should be well commented to clearly explain why your algorithm is linear time and complete (guaranteed to find a solution if one exists). Hints:

- If the last 3 digits of (x + y) are z, then the last 3 digits of (z - x) are the last 3 digits of y.

- For a given program, the locations at which the output breaks into terms are fixed.

- A solution that has to iterate through the input list a large number of times is still linear time as long as the number of passes is bounded by a constant.

You can test your implementation by running the following command on your command line:  $ julia test/runtests.jl question-2

## Problem 3 (30 pts)

For this problem, you will be working with an implementation of a top-down stochastic synthesis algorithm, and will be applying it to solve symbolic regression problems.
Start by installing Node.js and npm using the instructions [here](https://nodejs.org/en/download/). Then, from the `question3/js-synth` directory, install the dependencies with:
$ npm install
To make sure everything is set up properly, ensure that the following command runs successfully without crashing. It could take up to a minute or so to run, and it's okay if some of the outputs say "INCORRECT".
$ node performance-eval.js 1  Edits since release:

- If you're using Windows, you may have to do the following: copy `package.json` from "solution\question3\js-synth\package.json" to "solution\question3\package.json". And in `main.js` replace the line `const __dirname = path.dirname(new URL(import.meta.url).pathname); ` with `const __dirname = path.resolve();`.

- There was a small visual bug where the displayed equation for one problem was slightly different from the function being graphed - this doesn't impact any of the printed results, just the label on one equation. "f(x) = 2 * sin(x) + sin(2 * x) + x" should instead have said "f(x) = 2 * sin(x) + sin(2 * x)"

### Problem 3a

Define a grammar for a symbolic regression language in the `lang` variable of `question3/question3a.js`. Refer to the annotated example grammar in `question3/js-synth/languages/simplmaplang.js` to understand the format. Your language should have:

- Arithmetic operations

- Trigonometric functions

- Exponentiation

- If-then-else conditional operator (with a boolean condition supporting less-than comparisons)

- Integer constants 0 through 5

- Input variable `x` (this will be handled for you by the library)

The functions being synthesized will have type `"float->float"`, and are listed in `problemDefinitions` at the top of `question3/gen_data.js`.
Note: Primitive function implementations should not throw errors, however NaN values are fine and the loss function will assign them the highest possible loss.

You can try out your implementation by running (from `question3/`)
node main.js You can run the starter code in the same way (but it will only synthesize identity, constant, and sin functions).
You can then launch a local server to view the results by running (from `question3/`)
python3 -m http.server 8989  Once launched, you can leave this process running in a separate terminal, no need to restart it between runs. Open [http://localhost:8989/visualization/synthesis_viewer.html](http://localhost:8989/visualization/synthesis_viewer.html) to view the results. You might find that many of the solutions appear much longer than the ground truth solutions - this is expected in the current configuration of the algorithm, which isn't heavily prioritizing shorter programs.

Finally, for a slower more thorough evaluation, you can benchmark your implementation by running
node main.js benchmark Which will run the synthesis algorithm 5 times and print the average results. Note that benchmarking will not update the results in the visualization.
Expected performance: Stochastic synthesis algorithms will vary between runs, so we don't expect every run to find an exact solution. Additionally, synthesis can get stuck in local optima that prevent finding the exact solution. We therefore don't expect your implementation to solve all of the problems exactly, nor to do so every time. It should be possible to solve many of the easier problems exactly fairly often, but it is okay to solve the later problems much less frequently - and having an average loss that is below 0.1 (1e-1) for each problem will get full credit.
For reference, a benchmarking run of our implementation (a fairly general grammar, not particularly specialized to the problems) gave the following results:  f(x) = x: harmonicAvgLoss = 0.00e+0, avgLoss = 0.00e+0, avgCost = 11, fracCorrect = 1 f(x) = 5 * x + 10: harmonicAvgLoss = 2.25e-34, avgLoss = 9.09e-34, avgCost = 2856.6, fracCorrect = 1 f(x) = 5 / x^2: harmonicAvgLoss = 0.00e+0, avgLoss = 6.54e-36, avgCost = 8855.2, fracCorrect = 1 f(x) = (sin(x))^3: harmonicAvgLoss = 5.34e-33, avgLoss = 5.34e-33, avgCost = 1489.8, fracCorrect = 1 f(x) = if(lt(x, 0), 0, x): harmonicAvgLoss = 0.00e+0, avgLoss = 0.00e+0, avgCost = 1609, fracCorrect = 1 f(x) = if(lt(x, 0), 3 * x ^ 2, x * sin(x)): harmonicAvgLoss = 2.54e-33, avgLoss = 5.63e-3, avgCost = 49509, fracCorrect = 0.2 f(x) = 2 * sin(x) + sin(2 * x) + x: harmonicAvgLoss = 0.00e+0, avgLoss = 2.44e-2, avgCost = 49939.8, fracCorrect = 0.2 f(x) = 4 * x^2 - 5 * x + 4: harmonicAvgLoss = 8.78e-31, avgLoss = 9.51e-3, avgCost = 47907, fracCorrect = 0.2 f(x) = sin(2 * x^2)/cos(x^2): harmonicAvgLoss = 7.46e-33, avgLoss = 7.46e-33, avgCost = 22754.8, fracCorrect = 1 f(x) = if(lt(x, 1), (2-x), sin(x)): harmonicAvgLoss = 0.00e+0, avgLoss = 2.69e-3, avgCost = 27667.8, fracCorrect = 0.8 f(x) = 4 * (sin(x))^3 + x: harmonicAvgLoss = 3.31e-32, avgLoss = 3.53e-3, avgCost = 46899, fracCorrect = 0.2  But your results will vary with your choice of grammar. Here avgLoss is the average loss over all runs, avgCost is the average number of synthesis steps taken before a solution was found (if any), and fracCorrect is the fraction of runs that found an exact solution.

### Problem 3b

Language models can often struggle with the kind of reasoning required for symbolic regression from input-output examples. Try prompting a language model of your choice (e.g. ChatGPT) to see if it can solve some of these problems - pick 3 problems of varying difficulty to try.
Write your own prompt, and be sure to provide the grammar along with (some or all of) the input-output examples for the problem (you can find these in `problems.json`).
Briefly describe the model and prompt you used, and summarize your takeaways from doing this with 3 problems of varying difficulty. What can or can't it solve? How does it's reasoning go wrong or right? We will be grading this part based on effort as opposed to outcomes. Record your answer in `question3b.txt`.
