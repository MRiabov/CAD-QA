# Human Paper Spec Notes

## Initial human suggestion

I have this idea for a dataset:
A dataset of QA pairs for CAD. Given a CadQuery script, answer questions like:
"In this point in space, which feature has last contributed to adding volume to it?"
"How much volume does a subtractive filet over all Z axes would have?"
"How much edges are there in a script?"
"How much many X-axis edges does the script have?"
"How big is the distance between point A and point B"?
"How much volume would this extrude add?"
"How points and edges would this extrude add?"

Are there any improvement to the dataset you may suggest?

Why I care: LLMs are stlll bad at understanding CAD. Perhaps QA dataset training would allow improvements on it.

## Additional human notes

Additional notes are graph-like reasoning:

* "How much volume does the feature that comes after the second box contribute to the volume?"
* "What is the length of the axis for the feature that has 8 parallel edges?"
* "Of boxes with parameters (1,2,3) and (4,5,6), which changed the bounding-box volume more?"
* "Of boxes with parameters (1,2,3) and (4,5,6), which has changed the bounding box more on the Y axis?"
* "How much volume did the cylinder A subtract from box B?"
* "How much X distance is between the first hole and the third hole in the script?"
* "What is the length of the feature that added the most volume?"

## A bit of diversity

* "Given this script we intend to add feature box(1,2,3)."
* "What is the weight added by feature A, provided the material has density 8.27 g/cm^3?"
* "What is the shortest distance between the centerlines of the first hole and the second cylinder in the script?"

### Bounding box as selectors

Not mentioned above: "in the bounding box of min=(1,2,3) and max=(4,5,6), which features have:
* Added/removed volume
* have at least one vertices
* How many vertices there are

Ad nauseam. And the other tasks bounding boxes may introduce.

## Adding graphs and graph-like QA generation

So the task here is twofold:
1. One-shot questions (covered before the "additional human notes")
2. Graph-like reasoning with figuring out what the user has asked, then proving it.
