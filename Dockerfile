FROM continuumio/miniconda3

WORKDIR /src/c3s-eqc-data-checker

COPY environment.yml /src/c3s-eqc-data-checker/

RUN conda install -c conda-forge gcc python=3.10 \
    && conda env update -n base -f environment.yml

COPY . /src/c3s-eqc-data-checker

RUN pip install --no-deps -e .
