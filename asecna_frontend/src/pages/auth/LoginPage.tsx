import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../store/authContextValue'
import { Eye, EyeOff, Loader2, Shield } from 'lucide-react'
import { apiErrorMessage } from '../../api/client'

export default function LoginPage() {
    const { login } = useAuth()
    const navigate = useNavigate()
    const [matricule, setMatricule] = useState('')
    const [password, setPassword] = useState('')
    const [showPassword, setShowPassword] = useState(false)
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')
        setLoading(true)
        try {
            await login(matricule, password)
            navigate('/dashboard')
        } catch (err: unknown) {
            setError(apiErrorMessage(err, 'Matricule ou mot de passe incorrect.'))
        } finally {
            setLoading(false)
        }
    }

    return (
        <div
            className="min-h-screen flex items-center justify-center relative overflow-hidden"
            style={{
                backgroundImage: `url('/asecna_bg.jpg')`,
                backgroundSize: 'cover',
                backgroundPosition: 'center',
            }}
        >
            {/* Overlay sombre */}
            <div className="absolute inset-0 bg-gradient-to-br from-black/70 via-asecna-950/60 to-black/80" />



            {/* Panneau de connexion */}
            <div className="relative z-10 w-full max-w-md mx-4">

                {/* Logo + Identité */}
                <div className="text-center mb-8">
                    <div className="flex justify-center mb-4">
                        <div className="w-24 h-24 rounded-full overflow-hidden border-4 border-white/30 shadow-2xl bg-white/10 backdrop-blur flex items-center justify-center">
                            <img
                                src="/asecna_logo.png"
                                alt="Logo ASECNA"
                                className="w-full h-full object-cover"
                                onError={e => {
                                    (e.target as HTMLImageElement).style.display = 'none'
                                }}
                            />
                            <Shield size={40} className="text-asecna-400 absolute" />
                        </div>
                    </div>
                    <h1 className="text-4xl font-bold text-white tracking-wide">ASECNA</h1>
                    <p className="text-asecna-300 text-sm mt-1 font-light tracking-wider uppercase">
                        Système de Gestion des Agents
                    </p>
                    <div className="flex items-center justify-center gap-2 mt-3">
                        <div className="h-px w-12 bg-white/20" />
                        <span className="text-white/40 text-xs">Espace personnel sécurisé</span>
                        <div className="h-px w-12 bg-white/20" />
                    </div>
                </div>

                {/* Carte formulaire */}
                <div className="bg-white/10 backdrop-blur-xl rounded-3xl p-8 border border-white/20 shadow-2xl">
                    <h2 className="text-xl font-semibold text-white mb-1">Connexion</h2>
                    <p className="text-white/50 text-sm mb-6">Entrez vos identifiants ASECNA</p>

                    {error && (
                        <div className="bg-red-500/20 border border-red-400/40 rounded-xl p-3 mb-5 flex items-center gap-2">
                            <div className="w-1.5 h-1.5 rounded-full bg-red-400 flex-shrink-0" />
                            <p className="text-red-200 text-sm">{error}</p>
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div>
                            <label className="block text-sm font-medium text-gray-200 mb-2">
                                Matricule
                            </label>
                            <input
                                id="matricule"
                                type="text"
                                value={matricule}
                                onChange={e => setMatricule(e.target.value.trim())}
                                placeholder="ASE-XXXX-XXXX"
                                required
                                autoComplete="username"
                                className="w-full bg-white/10 border border-white/20 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-asecna-400 focus:border-transparent transition-all text-sm"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-200 mb-2">
                                Mot de passe
                            </label>
                            <div className="relative">
                                <input
                                    id="password"
                                    type={showPassword ? 'text' : 'password'}
                                    value={password}
                                    onChange={e => setPassword(e.target.value)}
                                    placeholder="••••••••"
                                    required
                                    autoComplete="current-password"
                                    className="w-full bg-white/10 border border-white/20 rounded-xl px-4 py-3 pr-12 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-asecna-400 focus:border-transparent transition-all text-sm"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white transition-colors p-1"
                                    tabIndex={-1}
                                >
                                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                                </button>
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={loading || !matricule || !password}
                            className="w-full bg-asecna-600 hover:bg-asecna-500 active:bg-asecna-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-3.5 px-4 rounded-xl transition-all duration-200 flex items-center justify-center gap-2 mt-1 shadow-lg shadow-asecna-900/50"
                        >
                            {loading ? (
                                <>
                                    <Loader2 size={17} className="animate-spin" />
                                    Connexion en cours...
                                </>
                            ) : 'Se connecter'}
                        </button>
                    </form>

                    <div className="mt-6 pt-5 border-t border-white/10 text-center">
                        <p className="text-xs text-white/30 leading-relaxed">
                            Accès réservé au personnel ASECNA.<br />
                            En cas de problème de connexion, contactez votre administrateur.
                        </p>
                    </div>
                </div>

                {/* Footer */}
                <p className="text-center text-white/20 text-xs mt-6">
                    © {new Date().getFullYear()} ASECNA — Agence pour la Sécurité de la Navigation Aérienne
                </p>
            </div>
        </div>
    )
}
