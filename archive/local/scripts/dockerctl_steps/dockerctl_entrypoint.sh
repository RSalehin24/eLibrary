wait_docker() {
  echo "Waiting for Docker..."
  until docker info >/dev/null 2>&1; do
    sleep 2
  done
  echo "Docker is ready."
}

cmd="${1:-start}"

case "$cmd" in
  start)
    ensure_macos_tools

    if is_macos; then
      if colima status 2>&1 | grep -qi "running"; then
        echo "Colima already running."
      else
        start_colima
      fi
      wait_docker
      docker context show
    else
      echo "Non-macOS detected."
      if have_cmd docker; then
        echo "Docker is installed."
        docker info >/dev/null 2>&1 && echo "Docker daemon is reachable." || echo "Docker CLI found, but daemon is not reachable."
      fi
    fi
    ;;

  stop)
    if is_macos; then
      if ! have_cmd colima; then
        echo "Colima is not installed."
        exit 1
      fi
      echo "Stopping Colima..."
      colima stop
      echo "Stopped."
    else
      echo "Non-macOS detected."
      echo "Please stop Docker using your system's service manager."
      exit 1
    fi
    ;;

  restart)
    ensure_macos_tools

    if is_macos; then
      echo "Restarting Colima..."
      colima stop || true
      start_colima
      wait_docker
    else
      echo "Non-macOS detected."
      echo "Please restart Docker using your system's service manager."
      exit 1
    fi
    ;;

  reset)
    ensure_macos_tools

    if is_macos; then
      echo "Force resetting Colima (this removes Colima VM data)..."
      colima stop -f || true
      colima delete -f || true
      rm -rf "$HOME/.lima/colima"
      rm -rf "$HOME/.colima/_templates/colima.yaml" "$HOME/.colima/colima.yaml"
      colima start --runtime docker
      wait_docker
    else
      echo "Non-macOS detected."
      echo "Reset is only supported here for macOS + Colima."
      exit 1
    fi
    ;;

  status)
    if is_macos && have_cmd colima; then
      colima status || true
    fi
    if have_cmd docker; then
      docker info || true
    else
      echo "Docker is not installed."
    fi
    ;;

  help|-h|--help)
    show_help
    ;;

  *)
    echo "Unknown command: $cmd"
    echo
    show_help
    exit 1
    ;;
esac
