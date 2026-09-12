# Makefile for the AgenticOS 2026 workshop manuscript (track 1 vision paper).
#
# This manuscript does not include any external figure file: the only figure is
# an inline TikZ picture in main.tex, so there is no figures/ prerequisite.
#
# acmart.cls and ACM-Reference-Format.bst are vendored at the repository root,
# so TEXINPUTS/BSTINPUTS must point there. The local directory must come first:
# with the class directory ahead of ".", kpathsea resolves the bare "main"
# argument to the repository-root main.tex instead of this workshop source.

# Main document (without .tex extension)
MAIN = main

# LaTeX compiler
LATEX = pdflatex
BIBTEX = bibtex

# Directories holding the vendored acmart.cls and ACM-Reference-Format.bst.
CLSDIR = ../..

# Local directory first, then the class directory, then the defaults.
export TEXINPUTS := .:$(CLSDIR):$(TEXINPUTS)
export BSTINPUTS := .:$(CLSDIR):$(BSTINPUTS)

# All source files
TEXFILES = $(wildcard *.tex)
BIBFILES = $(wildcard *.bib)

.PHONY: all clean distclean

all: $(MAIN).pdf

$(MAIN).pdf: $(MAIN).tex $(TEXFILES) $(BIBFILES)
	$(LATEX) -interaction=nonstopmode ./$(MAIN).tex
	$(BIBTEX) $(MAIN)
	$(LATEX) -interaction=nonstopmode ./$(MAIN).tex
	$(LATEX) -interaction=nonstopmode ./$(MAIN).tex

clean:
	rm -f *.aux *.log *.bbl *.blg *.out *.toc *.lof *.lot *.fls *.fdb_latexmk *.synctex.gz comment.cut

distclean: clean
	rm -f $(MAIN).pdf
