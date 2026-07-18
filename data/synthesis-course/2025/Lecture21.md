---
source: https://people.csail.mit.edu/asolar/SynthesisCourse/2025/Lecture21.htm
original_file: Lecture21.htm
---

Lecture 19

# Introduction to Program Synthesis

© Armando Solar-Lezama. 2018. All rights reserved.

# Lecture 21: Expressive Types

(Developed in collaboration with Nadia Polikarpova from materials from her course)

Back in [Lecture 4](Lecture4.md) we saw how types could be used to aggressively prune the search space. A key benefit of the type-based reasoning was the ability to locally determine that a partially constructed program could never be completed to become a full program and therefore all possible completions of this partially constructed program could be safely discarded from the search. The types explored in that lecture, however, were not particularly expressive, so although they could greatly aid the search in an inductive synthesis setting, they were not sufficient in themselves to fully describe the computation.

In this lecture, we will explore a more expressive type system that is capable of more aggressively restricting the search space while still keeping type-checking tractable. In particular, we will be exploring refinement types, which are decorated with predicates from a decidable logicKnowles:2010 RondonKJ08. Over the rest of this lecture, we follow the approach of Rondon, Kawaguchi and Jhala from their PLDI'08 paperRondonKJ08, which later became the basis of the synthesis work of Polikarpova, Kuraj and Solar-LezamaPolikarpova:2016.

Lecture15:Slide16; Lecture15:Slide17; Lecture15:Slide18; Lecture15:Slide19; Lecture15:Slide20; Lecture15:Slide21; Lecture15:Slide22; Lecture15:Slide23  In this formalism, it is possible to define types of the form: \[ \{ \nu : B | P(\nu) \} \] Where $B$ is a base type, $\nu$ is a fresh name that is given to values of that type, and $P$ is a predicate on $\nu$. Informally, such a type corresponds to the set of all values of type $B$ that satisfy the predicate $P$. Simple examples of such a type include the type $\{ \nu : Int | \nu \geq 0 \}$, the type of natural numbers often named $Nat$, or $\{ \nu : Int | a \geq \nu \geq b \}$, the type of values in the closed range $[a,b]$. For functions, the types give names to the parameters, and the predicates can refer to these parameters. For example, the type \[ x:T \rightarrow \{ \nu : B | P(x, \nu) \} \] corresponds to a function with a named argument of type $T$, and a result whose predicate can depend on the parameter $x$. The figure shows the more general form of the type definitions. The figure uses the notation $\Gamma \vdash e :: T$ to refer to the typing judgement where expression $e$ has type $T$ under an environment $\Gamma$.

The figure shows some of the basic typing rules for the type system. However, as the examples in the figure show, these rules are insufficient even to prove some fairly trivial properties. In order to really leverage the power of this type system, it is necessary to have some subtyping rules that allow us to match types with different predicates.  Lecture15:Slide24; Lecture15:Slide25; Lecture15:Slide40; Lecture15:Slide26; Lecture15:Slide27; Lecture15:Slide28; Lecture15:Slide29; Lecture15:Slide30; Lecture15:Slide31; Lecture15:Slide32; Lecture15:Slide33; Lecture15:Slide34; Lecture15:Slide35; Lecture15:Slide36; Lecture15:Slide37; Lecture15:Slide38; Lecture15:Slide39

In general, when we say that a type $T_1$ is a subtype of $T_2$, written as $T_1 <: T_2$, it means that a value of type $T_1$ can use in a context that was expecting a type $T_2$. For basic types, this can happen when the subtype represents a subset of the values represented by the supertype. Note that the subtyping rule for basic types requires us to be able to extract constraints from the environment $\Gamma$. Also note that $\Gamma$ can have constraints in addition to mappings from variables to types. These constraints are added by the rule for `if` conditions as shown in the figure. The examples illustrate why extracting constraints from the environment is so important. For example, in the first example in the figure, we need to prove that $\{\nu:Int | \nu = y\} <: \{\nu:Int | \nu > 0 \}$. In general, this is not true, but it is true in this context because the environment has information that $y>0$. The figure shows how the subtyping rules now allow us to prove the properties that could not be proven before.

## Complex properties with refinement types

The type system outlined above can describe some fairly complex specifications when combined with standard type system features such as polymorphism.  Lecture15:Slide2; Lecture15:Slide41; Lecture15:Slide42; Lecture15:Slide43

For example, consider the example of the `replicate` function in the figure. Using a standard type system, we can express the fact that given a length parameter and an input value, it can produce a list of values of the same type as the second input. However, using refinement types we can add the constraint that the length of the output list should be equal to the `n` parameter. The figure also shows how refinement types can help catch errors that conventional types cannot catch. In the example, the insert function does not satisfy the stated specification, but the conventional types are unable to catch the error. However, using refinement types it is possible to define a type signature in terms of a sorted list type `SList`. Moreover, the type signature is defined in terms of a function `elems` which maps a list to its set of elements. Now, with the richer type signature, the type checker is able to catch the error because there is a type mismatch between the type that is expected, where $elems~ \nu = elems~ xs \cup \{x\}$, and the best type that the type checker was able to compute, where $elems~ xs \subseteq elems~ \nu$.
