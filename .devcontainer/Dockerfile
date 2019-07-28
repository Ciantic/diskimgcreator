# Partfs build
FROM debian:buster-slim as partfs-build
RUN apt-get update -qq -y && apt-get -y install \
    build-essential gcc cmake libfdisk1 libfdisk-dev libfuse-dev libfuse2 git fuse
RUN git clone https://github.com/braincorp/partfs /build/partfs
RUN cd /build/partfs && make

# Main image
FROM debian:buster-slim as main
RUN apt-get update -qq -y && apt-get -y install \
    libfdisk1 libfuse2 fuse \
    dosfstools parted python3
COPY --from=partfs-build /build/partfs/build/bin/partfs /usr/local/bin/partfs
COPY ./src/diskimgcreator.py /
RUN chmod +x /diskimgcreator.py
WORKDIR /disk
ENTRYPOINT ["/diskimgcreator.py"]

# Main development env
FROM main
RUN apt-get update -qq -y && apt-get -y install \
    python3-pip git
ENV PATH="/root/.local/bin:${PATH}"
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3  2
RUN /usr/bin/python3 -m pip install -U pylint --user && \
    /usr/bin/python3 -m pip install -U black --user && \
    /usr/bin/python3 -m pip install -U rope --user