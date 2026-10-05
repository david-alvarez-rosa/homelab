window.addEventListener("keydown", (e) => {
  if (e.key !== "Escape" || e.ctrlKey || e.altKey || e.metaKey || e.shiftKey || e.isComposing) return;
  if (!location.hash.startsWith("#/room/")) return;
  const t = e.target;
  if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT")) return;
  if (document.querySelector(".mx_Dialog_wrapper, .mx_ContextualMenu, .mx_ReplyPreview, .mx_EditMessageComposer, .mx_Autocomplete_Completion, .mx_RoomView_searchResultsPanel")) return;
  setTimeout(() => { location.hash = "#/home"; });
}, true);
