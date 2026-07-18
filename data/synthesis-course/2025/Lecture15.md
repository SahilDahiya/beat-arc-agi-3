---
source: https://people.csail.mit.edu/asolar/SynthesisCourse/2025/Lecture15.htm
original_file: Lecture15.htm
---

Lecture 15

# Introduction to Program Synthesis

© Armando Solar-Lezama, 2025. All rights reserved.

# Lecture 15: Agents [(Slides)](https://code.playskript.com/view.html?id=cb9e2508575655259a663d4d5f84e9df620cf9023a6f5e6dd4)

The combination of LLMs and genetic algorithms we saw in the previous lecture is just one example of a broader class of systems that incorporate LLMs into larger workflows that include other code and algorithms in order to solve a problems. In recent years, there has been a lot of interest in building such systems, often called agents.

We can begin a very broad classification of agents into two categories: Program-in-control and LLM-in-control. A program-in-control agent is basically a python program that invokes an LLM to help it solve the problem. There is a broad range of such agents, depending on how much of the problem solving is done by the LLM versus by the program. At one end of the spectrum, we have search-based agents, where the program implements a generic search strategy, but where all the problem specific logic is done by the LLM. At the other end of the spectrum, we have domain-specific workflows, where the program implements a workflow that is specific to the problem at hand, and where the LLM is just invoked to perform sub-tasks that cannot be performed with traditional code.

An LLM-in-control agent is basically an LLM that is augmented with the ability to invoke code to help it solve problems. This is often referred to as tool use, but it can be more general than that. In some cases, the LLM is not limited to the use of existing tools, but can also generate code to solve a sub-task that is better suited to algorithmic solution. In the rest of this lecture, we elaborate on these different kinds of agents.

## Search-based agents

Agents:meta-generation; Agents:TreeOfThought  In many situations, the problem we want to solve can in principle be solved by an LLM, but the LLM is not reliable enough to ensure that the solution it provides is correct. In such situations, it is common to use code to orchestrate repeated invokations of the LLM in order to search for a correct solution.

Welleck et alWelleck2024_FromDecodingToMetaGeneration call these meta-generation algorithms, and they provide a good survey of them. Snell et al.Snell2025_ScalingLLMTestTimeCompute also explore several such algorithms and argue that scaling test time compute can be more effective than scaling model size for improving performance on reasoning tasks.

The figure illustrates some of the meta-generation algorithms described by Welleck et al. Parallel search involves invoking the LLM multiple times in parallel to generate candidate solutions, and then evaluating them aggregating their solutions to produce a final answer. Heuristic step-level search involves generating many partial solutions, and then selecting among them to chose next step of the solution. Refinement involves generating tentative solutions and then asking a model to critique them and then using the last solution and the generated feedback to ask the model to improve the solution.

In NeurIPS 2023, Yao et al Yao2023_TreeOfThoughts introduced an algorithm that has become fairly popular called Tree of Thoughts, which performs a tree search over the outputs of an LLM. The idea is to perform a tree search over the outputs of the model, but instead of doing it at the granularity of tokens, to do it at the granularity of “thoughts”, which are coherent units of text that represent one step in a reasoning process.

## Domain specific workflows

Agents:LMQL-ex1; Agents:LMQL-ex2; Agents:LMQL-ex3; Agents:LMQL-ex4  There are many situations where we want to build more specialized workflows that are tailored to a specific problem. There has been some recent work on building languages and frameworks for specifying such workflows. A particularly notable one from the programming languages community is the LMQL languagebeurer2023lmql. The basic idea in this language is to provide simple syntax to support the user to describe workflows where information provided by an LLM in one step is used to construct the prompt for the next step.

The figure shows some examples that showcase the use of LMQL (from the LMQL paper)beurer2023lmql. The basic idea of LMQL is that you can write a prompt template that uses variables in brackets to indicate places where information will be filled in by the LLM, and then you can use those variables in later parts of the prompt. Interspersed with the prompt, you can use Python code to process the outputs of the LLM and to compute values that will be used in later parts of the prompt.

The language also allows the user to specify constraints on the outputs of the LLM, and the LMQL runtime will ensure that the outputs satisfy those constraints.

## LLM-in-control style agents

Agents:linc1; Agents:linc2; Agents:linc3; Agents:linc4; Agents:linc5; Agents:linc6; Agents:linc7; Agents:vipergpt1; Agents:vipergpt2; Agents:vipergpt3; Agents:vipergpt4; Agents:vipergpt5  In contrast to the program-in-control agents we have seen so far, there has been a lot of recent interest in LLM-in-control agents, where the LLM is the main driver of the problem solving process, but where it is augmented with the ability to invoke code. A simple example of this is the tool-use paradigm, where the LLM is given access to a set of tools (APIs) that it can invoke to help it solve problems. One example of this is the LINC paper which explored the use of a theorem prover to solve logical problems that may otherwise be too difficult for the LLM to solve on its ownOlaussonGLZSTL23. In this case, the LLM is prompted to translate the problem into the input notation of the [Prover 9 theorem prover](https://www.cs.unm.edu/~mccune/mace4/) so it can leverage the reasoning capabilities of the theorem prover.

This idea of leveraging code generation for problem solving was the basis of the ViperGPT projectSuris2023_ViperGPT, which explored the idea of using an LLM to generate code to solve a problem instead of solving the problem directly. The focus of the paper was on visual reasoning tasks, and the LLM was given access to an API with a set of machine vision primitives and was prompted to generate code that uses those primitives to solve the visual reasoning task.

A similar idea was explored in the Chain of Code paperLi2024_ChainOfCode, which also generates code to solve problems rather than solving them directly. A big novelty in this paper is that the generated code may invoke functions that are not implemented in code. When the interpeter reaches one such function, it calls the LLM to emulate the function.
