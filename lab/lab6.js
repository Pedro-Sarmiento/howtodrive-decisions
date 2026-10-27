async () => {
  // Vuelca now y p(acción) para todas las frases que no corta la regla.
  const { Classifier } = await import('/node_modules/.vite/deps/runonweb_classify.js').catch(() => ({}))
  return { hasBench: typeof window.bench, Classifier: typeof Classifier }
}
