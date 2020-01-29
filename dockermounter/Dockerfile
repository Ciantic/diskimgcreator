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
COPY ./src/diskimgmounter.py /
COPY ./src/diskimgcreator.py /
RUN chmod +x /diskimgmounter.py
WORKDIR /disk
ENTRYPOINT ["python3", "/diskimgmounter.py", "/image.img", "--use-partfs"]
CMD ["--help"]

# Released version
FROM main