import { Link } from 'react-router-dom'
import { Compass } from 'lucide-react'

/** Page affichée pour toute URL ne correspondant à aucune route. */
export default function NotFoundPage() {
    return (
        <div className="min-h-screen flex items-center justify-center p-6">
            <div className="card max-w-md text-center">
                <Compass size={44} className="mx-auto mb-4 text-asecna-500" />
                <h1 className="text-2xl font-bold text-gray-900">Page introuvable</h1>
                <p className="text-gray-500 text-sm mt-2">
                    L'adresse demandée n'existe pas ou n'est plus accessible.
                </p>
                <Link
                    to="/dashboard"
                    className="inline-block mt-6 px-4 py-2.5 rounded-xl bg-asecna-600 text-white text-sm font-medium hover:bg-asecna-700 transition-colors"
                >
                    Retour au tableau de bord
                </Link>
            </div>
        </div>
    )
}
