FROM registry.redhat.io/ubi9/python-39:latest

# 1. Switch to root to handle system-level directory setup
USER root

# 2. Replicate the DRC structure under /opt/drc
WORKDIR /opt/drc

# 3. Copy the entire tree from your local DRC folder
COPY . .

# 4. Install PyYAML (which provides the 'yaml' module)
RUN pip install --no-cache-dir PyYAML

# 5. Fix permissions for the UBI default user (1001) and root group (0)
RUN chown -R 1001:0 /opt/drc
RUN chmod -R g=u /opt/drc

# 6. Set Environment Variables so Python sees the parent directory
ENV PYTHONPATH="/opt/drc"

# 7. Move into the 'js' folder
WORKDIR /opt/drc/js

# 8. Switch to the non-root user
USER 1001

EXPOSE 8081

# 9. Run the bridge script with unbuffered output
CMD ["python", "-u", "bridge_server.py"]
