/**
 * Mise en place commune aux tests frontend.
 *
 * `@testing-library/jest-dom` ajoute les assertions de DOM
 * (`toBeInTheDocument`, `toBeDisabled`, ...) au `expect` de Vitest.
 */
import '@testing-library/jest-dom/vitest'
import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

// Chaque test repart d'un DOM vide : sans cela, deux rendus successifs
// coexistent et les requetes `getBy*` echouent sur un doublon.
afterEach(() => cleanup())
