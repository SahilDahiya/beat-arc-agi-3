---
source: https://people.csail.mit.edu/asolar/SynthesisCourse/2025/index.htm
original_file: index.htm
---

Introduction to Program Synthesis

# 6.5130 Introduction to Program Synthesis Fall 2025

© Armando Solar-Lezama. 2025. All rights reserved.

[Lecture 1](index.md#about) [Lecture 2](index.md#services) [Lecture 3](index.md#clients) [Lecture 4](index.md#contact)

# Introduction to program synthesis

Lecture0:Slide0; Lecture0:Slide1; Lecture0:Slide2; Lecture0:Slide3; Lecture0:Slide4; Lecture0:Slide5; Lecture0:Slide6; Lecture0:Slide7;

# Anouncements

Welcome to 6.5130!
When/Where: MW1-2.30 in room 66-168

This webpage is a work in progress for the 2025 offering of the course. The course has changed quite substantially from previous offerings, with a stronger emphasis placed on language models and deep learning. If you are interested in a more symbolic version of the course, check out the 2023 version [here.](http://people.csail.mit.edu/asolar/SynthesisCourse2023/index.htm)

Monday 9/8:  Pset 1 is now posted. You can find it [here](Assignment1.md).

Friday 10/3:  The first part of Pset 2 is now posted. You can find it [here](Assignment2.md).

# Course description

This course aims to give an introduction to program synthesis, an exciting field at the intersection of programming languages, formal methods and AI. The course will explore a number of fundamental questions around the problem of how to automatically generate programs that do what the user wants. In particular, the class will explore the following questions:

- The intention question: how does the user convey intent and how do we increase the likelihood that the synthesizer will produce the desired program even when the specification is ambiguous or incomplete?

- Interplay between program search and program verification: how do we ensure that the program we synthesize will actually be deemed correct by a potentially brittle verification mechanism, and how do we use a verifier to our advantage to help synthesize programs faster?

- Interplay between program synthesis and deep learning: how do you reconcile the symbolic techniques traditionally used for synthesis and verification with deep learning? We will explore learning based techniques including language models based on transformers and reinforcement learning.

- Program synthesis beyond software engineering: the course will also discuss applications of program synthesis beyond automated programming to other domains where one has to generalize from small number of examples and produce interpretable models, as well as neurosymbolic learning techniques that combine ideas from program synthesis with ML.

## Grading

The course will be graded based on four hands-on assignments as well as a final project where you will get to apply the concepts learned in the course to the problem of your choice. This course counts for the TQE requirement.

- Assignment 1: 15%

- Assignment 2: 15%

- Assignment 3: 15%

- Assignment 4: 15%

- Project: 40%

All psets are due at 5pm on the posted day. The late penalty will be 10 points per day up to a maximum of 4 days.

## Project

An important part of the grade will be a term project where students will demonstrate their mastery of the topics covered in the course. The projects can apply concepts from the course to a new problem, or explore new techniqes. The project grade be based on the following benchmarks:

-  Team composition (2.5%): You must register your team here before Tuesday October 4.

-  One-page project proposal (12.5%): The proposal should describe what you plan to do for the project. The proposal should include information about preliminary work towards the project (for example, references to papers you have read related to what you plan to do, or to tools you have decided to use). For team projects, each team member should submit their own proposal describing their individual understanding of the project and their expected contribution.

-  Project presentation (10%): This will be an oral presentation on the last week of class where you will report on the outcome of your project. Each team will receive a single presentation slot, but each member of the team will have to present individually on their part of the project.

-  Project report (15%): The report should be between 4 and seven pages in the format provided. The project will be graded based on quality of execution, originality and scope. It is not necessary to have a positive result in order to obtain full credit. For team projects, each team member will need to submit an independent report; the reports of different team members can share up to 50% of common content, but the other half must reflect the contributions of each individual team member.
