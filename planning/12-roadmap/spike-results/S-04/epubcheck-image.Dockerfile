FROM debian:trixie-slim
RUN apt-get update && apt-get install -y --no-install-recommends openjdk-21-jre-headless unzip \
 && rm -rf /var/lib/apt/lists/*
COPY epubcheck-5.4.0.zip /tmp/
RUN unzip -q /tmp/epubcheck-5.4.0.zip -d /opt && rm /tmp/epubcheck-5.4.0.zip
ENTRYPOINT ["java", "-Xmx256m", "-jar", "/opt/epubcheck-5.4.0/epubcheck.jar"]
