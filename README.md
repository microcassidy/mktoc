# mktoc

Sometimes you get PDFs that don't have a table of contents. 

This generates LaTeX code for TOC generation for compiled PDF. Chances are some modifications will 
need to happen for each document but this is the general idea that might work for a specific usecase.

# info

absolute path to input document is written into the output `.tex` file so it is
possible to generate the file from anywhere on the system so compilation is possible 
from anywhere. 

It's suggested that you use latexmk for complilation.
