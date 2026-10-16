// ?stress=1 pads every project to 20 phases and 30 items with filler rows, to prove the layout scales.
(function () {
  if (!/[?&]stress=1/.test(location.search)) return;
  const types = ["bug", "idea", "future_request"];
  for (const p of HUB.projects) {
    for (let i = p.phases.length; i < 20; i++)
      p.phases.push({ id: "f" + i, name: "Fase de relleno " + (i + 1) + " con un nombre bastante largo para probar el corte",
        notes: "Notas de relleno: texto largo para comprobar que las notas de fase no se salen de su caja aunque ocupen varias líneas y lleven rutas como C:/Users/moyad/Documents/Visual Projects.",
        status: "todo" });
    for (let i = p.items.length; i < 30; i++)
      p.items.push({ id: "i" + i, type: types[i % 3], status: "open", created_at: HUB.snapshot,
        title: "Ítem de relleno " + (i + 1) + ": título largo para comprobar el corte en la lista de ítems",
        details: "Detalle de relleno." });
  }
})();
