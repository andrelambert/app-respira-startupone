import { useEffect, useState } from 'react';

export function useDebounced<T>(valor: T, ms: number): T {
  const [atual, setAtual] = useState(valor);
  useEffect(() => {
    const t = window.setTimeout(() => setAtual(valor), ms);
    return () => window.clearTimeout(t);
  }, [valor, ms]);
  return atual;
}
