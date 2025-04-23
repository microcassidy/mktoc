from PyPDF2 import PdfReader
from pathlib import Path

import typing as tp
import re
import logging
import sys
import os
from argparse import ArgumentParser


log_level = logging.getLevelNamesMapping().get(os.environ.get("LOG_LEVEL","CRITICAL"))

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, encoding="utf-8", level=log_level)

def get_content_line(txt):
    regex = re.compile(r'.*([ivx]+|[0-9]+)$')
    if regex.match(txt.strip()):
        return txt
    else:
        return None
def get_page_number(txt):
    regex = re.compile(r'([0-9xiv]+$)')
    search = regex.search(txt)
    assert search
    return search.group(1).strip()
def get_chapter_label(txt):
    regex = re.compile(r'^([0-9]+(\.?[0-9]+)?) ')
    search = regex.search(txt.strip())
    if search == None:
        return ''
    return search.group(1).strip()
    
def make_toc(chapter_labels,titles,page_numbers,stop,offset):
    assert len(chapter_labels) == len(titles)
    assert len(chapter_labels) == len(page_numbers)
    is_roman = lambda xs: any([x in set("xiv") for x in xs])
    end_of_toc = offset + stop
    def toc_line(label,title,page_number):
        typ = ["chapter","section"]
        depth = 0
        if "." in label:
            depth += 1 
        #the page numbers need to be indexed relative to the end of the toc
        #i.e. the original page numbering
        output_pagenumber = end_of_toc + int(page_number)
        logger.info(f"end_of_toc: {end_of_toc}\tinput page: {page_number}\toutput page {output_pagenumber}")

        return f"\t{end_of_toc + int(page_number)},{typ[depth]},{depth},{{{title + f" pg.{page_number}"}}},a"

    toc = []
    N = len(chapter_labels)
    for idx,(label,title,page_number) in enumerate(zip(chapter_labels,titles,page_numbers)):
        if is_roman(page_number):
            print(f"skipping:{title}...roman numeral indexing")
            continue
        tl = toc_line(label,title,page_number)
        if idx < N - 1:
            tl += ','
        toc += [tl]
    return '\n'.join(toc)

def make_TeX(toc,start,stop,offset,pdf_path:Path):
    """
    start: page number that marks the start of TOC
    stop: page number that marks the end of TOC
    offset: count of uncounted pages at the beginning
    """
    start_of_toc = start + offset
    start_of_book = stop + offset + 1
    return rf"""
\documentclass{{book}}
\usepackage{{pdfpages}}
\usepackage[pagebackref]{{hyperref}}
%\usepackage[final]{{hyperref}}
%\hypersetup{{
%    colorlinks,
%    citecolor=black,
%    filecolor=black,
%    linkcolor=black,
%    urlcolor=black
%}}
\begin{{document}}
% The following lines are the only ones you need to edit.
%\noindent{{\bfseries{{\huge Contents}}\hfill Page No.\vspace \bigskipamount \par }}
\includepdf[pages=1-{start_of_toc - 1}]{{{pdf_path.resolve().__str__()}}}
\tableofcontents
\addcontentsline{{toc}}{{chapter}}{{Contents}}
\label{{contents}}
\includepdf[pages={start_of_book}-,
addtotoc = {{
    {toc}
}}]{{{pdf_path.resolve().__str__()}}}
\end{{document}}
"""

def main(path:tp.Union[Path,str],start,stop,offset:int = 0,output_path = Path('main.tex')):
    """
    start: starting index for table of contents of input document 
    stop: stop index for table of contents of input document 
    offset (optional): offset for start and stop. Useful when page numbering does not start from zero
    """
    if isinstance(path,str):
        path = Path(path)
    assert path.exists()
    assert path.suffix == '.pdf', f'expected a pdf, received {path.suffix}'
    pdf = PdfReader(path)

    lines = []
    #pages are indexed internally from zero, but humans count pages from 1
    start_of_toc = offset + start
    end_of_toc = offset + stop
    for i in range(start_of_toc - 1, end_of_toc):
        page = pdf.pages[i].extract_text()
        for line in page.split('\n'):
            l = get_content_line(line)
            if l:
                lines += [l]
    chapter_labels = []
    page_numbers = []
    titles = []
    for line in lines:
        chapter_label = get_chapter_label(line)
        tail = line[len(chapter_label):].strip()
        chapter_labels += [chapter_label]
        page_number = get_page_number(line)
        page_numbers += [page_number]
        title = tail[:-len(page_number)].strip()
        titles += [title]
    assert len(chapter_labels) == len(page_numbers),"page number and chapter labels do not match in length"
    toc = make_toc(chapter_labels,titles,page_numbers,stop,offset)
    with open(output_path,'w') as fp:
        print(f'writing to {output_path.resolve()}')
        fp.write(make_TeX(toc,start,stop,offset,path))

    

if __name__ == '__main__':
    parser = ArgumentParser() 
    parser.add_argument('-i',type = Path,help='input pdf path',required = True)
    parser.add_argument('-o',type = Path,help='output .tex path',default='main.tex')
    parser.add_argument('--start',type = int,help='starting page for TOC',required = True)
    parser.add_argument('--stop',type = int,help='stop page for TOC',required = True)
    parser.add_argument('--offset',type = int,help='number of uncounted pages eg. cover. useful when page sequence is cover1,cover2,1,2,...',default=0)
    args = parser.parse_args()
    main(args.i,args.start,args.stop,args.offset,args.o)
