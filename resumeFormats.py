alex_format = {
    """
%-------------------------
% Resume in LaTeX (Jinja2 template)
%-------------------------

\documentclass[letterpaper,11pt]{article}

\usepackage{latexsym}
\usepackage[empty]{fullpage}
\usepackage{titlesec}
\usepackage{marvosym}
\usepackage[usenames,dvipsnames]{color}
\usepackage{verbatim}
\usepackage{enumitem}
\usepackage[hidelinks]{hyperref}
\usepackage{fancyhdr}
\usepackage[english]{babel}
\usepackage{tabularx}
\input{glyphtounicode}

\pagestyle{fancy}
\fancyhf{}
\fancyfoot{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

% Adjust margins
\addtolength{\oddsidemargin}{-0.5in}
\addtolength{\evensidemargin}{-0.5in}
\addtolength{\textwidth}{1in}
\addtolength{\topmargin}{-.5in}
\addtolength{\textheight}{1.0in}

\urlstyle{same}
\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}

% Sections formatting
\titleformat{\section}{
  \vspace{-4pt}\scshape\raggedright\large
}{}{0em}{}[\color{black}\titlerule \vspace{-5pt}]

% Ensure that generated pdf is ATS parsable
\pdfgentounicode=1

%-------------------------
% Custom commands (unchanged)
\newcommand{\resumeItem}[1]{
  \item\small{{#1 \vspace{-2pt}}}
}
\newcommand{\resumeSubheading}[4]{
  \vspace{-2pt}\item
    \begin{tabular*}{0.97\textwidth}[t]{l@{\extracolsep{\fill}}r}
      \textbf{#1} & #2 \\
      \textit{\small#3} & \textit{\small #4} \\
    \end{tabular*}\vspace{-7pt}
}
\newcommand{\resumeSubSubheading}[2]{
    \item
    \begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}
      \textit{\small#1} & \textit{\small #2} \\
    \end{tabular*}\vspace{-7pt}
}
\newcommand{\resumeProjectHeading}[2]{
    \item
    \begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}
      \small#1 & #2 \\
    \end{tabular*}\vspace{-7pt}
}
\newcommand{\resumeSubItem}[1]{\resumeItem{#1}\vspace{-4pt}}
\renewcommand\labelitemii{$\vcenter{\hbox{\tiny$\bullet$}}$}
\newcommand{\resumeSubHeadingListStart}{\begin{itemize}[leftmargin=0.15in, label={}]}
\newcommand{\resumeSubHeadingListEnd}{\end{itemize}}
\newcommand{\resumeItemListStart}{\begin{itemize}}
\newcommand{\resumeItemListEnd}{\end{itemize}\vspace{-5pt}}

%-------------------------------------------
%%%%%%  RESUME STARTS HERE  %%%%%%%%%%%%%%%%%

\begin{document}

%----------HEADING----------
\begin{center}
    \textbf{\Huge \scshape {{ name|latex }} } \\ \vspace{1pt}
    \small
    {{ location|default(" ", true)|latex }}
    {% if phone %}$|$ {{ phone|latex }}{% endif %}
    {% if email %}$|$ \href{mailto:{{ email|e }}}{\underline{{ email|latex }}}{% endif %}
    {% if linkedin %}$|$ \href{https://{{ linkedin|e }}}{\underline{{ linkedin|latex }}}{% endif %}
    {% if github %}$|$ \href{https://{{ github|e }}}{\underline{{ github|latex }}}{% endif %}
\end{center}

%-----------EDUCATION-----------
{% if education %}
\section{Education}
  \resumeSubHeadingListStart
  {% for ed in education %}
    \resumeSubheading
       { {{ ed.school|latex }} }{ {{ ed.dates|latex }} }
       { {{ ed.degree|latex }} }{ {{ ed.location|default("", true)|latex }} }
    {% if ed.coursework %}
      \resumeItem{\textbf{Relevant Coursework}: {{ ed.coursework|join(', ')|latex }}}
    {% endif %}
  {% endfor %}
  \resumeSubHeadingListEnd
{% endif %}

%-----------TECHNICAL SKILLS-----------
{% if skills %}
\section{Technical Skills}
 \begin{itemize}[leftmargin=0.15in, label={}]
    \small{\item{
    {% if skills.languages %}
     \textbf{Programming Languages}{: {{ skills.languages|join(', ')|latex }}} \\
    {% endif %}
    {% if skills.frameworks %}
     \textbf{Frameworks \& Libraries}{: {{ skills.frameworks|join(', ')|latex }}} \\
    {% endif %}
    {% if skills.tools %}
     \textbf{Developer Tools}{: {{ skills.tools|join(', ')|latex }}}
    {% endif %}
    }}
 \end{itemize}
{% endif %}

%-----------EXPERIENCE-----------
{% if experiences %}
\section{Work and Leadership Experience}
  \resumeSubHeadingListStart
  {% for e in experiences %}
    \resumeSubheading
      { {{ e.title|latex }} }{ {{ e.dates|latex }} }
      { {{ e.company|latex }} }{ {{ e.location|latex }} }
      \resumeItemListStart
        {% for b in (e.bullets|default([]))[:5] %}
          \resumeItem{ {{ b|latex }} }
        {% endfor %}
      \resumeItemListEnd
  {% endfor %}
  \resumeSubHeadingListEnd
{% endif %}

%-----------PROJECTS-----------
{% if projects %}
\section{Projects}
  \resumeSubHeadingListStart
  {% for p in projects %}
    \resumeProjectHeading
      { \textbf{ {{ p.name|latex }} } $|$ \emph{ {{ (p.tech|default([]))|join(', ')|latex }} } }
      { {{ p.date|default("", true)|latex }} }
    \resumeItemListStart
      {% for b in (p.bullets|default([]))[:4] %}
        \resumeItem{ {{ b|latex }} }
      {% endfor %}
    \resumeItemListEnd
  {% endfor %}
  \resumeSubHeadingListEnd
{% endif %}

\end{document}

    """
}