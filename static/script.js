document.addEventListener("DOMContentLoaded", () => {
  const wrappers = document.querySelectorAll(".video-wrapper.video-lazy");

  wrappers.forEach((wrapper) => {
    const button = wrapper.querySelector(".video-play-button");
    const thumb = wrapper.querySelector(".video-thumb");

    if (!button || !thumb) {
      return;
    }

    button.addEventListener("click", () => {
      const youtubeId = wrapper.dataset.youtubeId;
      if (!youtubeId) return;

      // Prevent double-click creating multiple iframes
      if (wrapper.classList.contains("is-playing")) return;
      wrapper.classList.add("is-playing");

      const iframe = document.createElement("iframe");
      iframe.className = "video-iframe";
      iframe.src = `https://www.youtube.com/embed/${youtubeId}?autoplay=1&rel=0`;
      iframe.title = thumb.alt || "YouTube video player";
      iframe.allow =
        "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share";
      iframe.allowFullscreen = true;
      iframe.loading = "lazy";

      // When the iframe is fully loaded, fade it in and remove thumb + button
      iframe.addEventListener("load", () => {
        iframe.classList.add("is-ready");
        thumb.remove();
        button.remove();
      });

      // Keep the thumbnail visible while the iframe loads
      wrapper.appendChild(iframe);
    });
  });
});