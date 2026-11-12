import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../store/authContextValue'
import {
    LayoutDashboard, Users, ClipboardList, BookOpen,
    BookMarked, GraduationCap, FileText, Building2,
    LogOut, Award, Menu, X, ShieldCheck,
    Bell, ShieldAlert, UserCog, UserCircle, GitPullRequestArrow,
    type LucideIcon,
} from 'lucide-react'
import { useState, useRef } from 'react'
import { authApi } from '../api'
import type { User } from '../types'

// ─── Définition des menus par rôle ──────────────────────────────────────────

type NavItem = { to: string; label: string; icon: LucideIcon }

const NAV_ADMIN: NavItem[] = [
    { to: '/dashboard', label: 'Tableau de bord', icon: LayoutDashboard },
    { to: '/agents', label: 'Agents', icon: Users },
    { to: '/units', label: 'Unités', icon: Building2 },
    { to: '/probation', label: 'Probation', icon: ClipboardList },
    { to: '/mentoring', label: 'Mentorat', icon: BookOpen },
    { to: '/arcep', label: 'Carnet ARCEP', icon: BookMarked },
    { to: '/evaluations', label: 'Évaluations', icon: Award },
    { to: '/reports', label: 'Rapports', icon: FileText },
    { to: '/training', label: 'Formations', icon: GraduationCap },
    { to: '/training/maintenances', label: 'Maintien QF', icon: ShieldCheck },
    // Ces deux ecrans existaient cote API mais n'etaient atteignables que par
    // l'admin Django ou Swagger.
    { to: '/workflows', label: 'Approbations', icon: GitPullRequestArrow },
    { to: '/users', label: 'Comptes & roles', icon: UserCog },
    { to: '/audit', label: 'Journal d\'audit', icon: ShieldAlert },
]

const NAV_UNIT_CHIEF: NavItem[] = [
    { to: '/dashboard', label: 'Tableau de bord', icon: LayoutDashboard },
    { to: '/agents', label: 'Mon équipe', icon: Users },
    { to: '/probation', label: 'Probations', icon: ClipboardList },
    { to: '/mentoring', label: 'Mentorat', icon: BookOpen },
    { to: '/arcep', label: 'Carnets ARCEP', icon: BookMarked },
    { to: '/evaluations', label: 'Évaluations', icon: Award },
    { to: '/reports', label: 'Rapports', icon: FileText },
    { to: '/workflows', label: 'Approbations', icon: GitPullRequestArrow },
]

const NAV_APPROVER: NavItem[] = [
    { to: '/dashboard', label: 'Tableau de bord', icon: LayoutDashboard },
    // Le registre transversal est l'ecran principal de l'approbateur : il y
    // voit d'un coup tout ce qui attend sa decision, tous modules confondus.
    { to: '/workflows', label: 'Approbations', icon: GitPullRequestArrow },
    { to: '/reports', label: 'Rapports à approuver', icon: FileText },
    { to: '/mentoring', label: 'Mentorats soumis', icon: BookOpen },
    { to: '/evaluations', label: 'Évaluations', icon: Award },
]

const NAV_EVALUATOR: NavItem[] = [
    { to: '/dashboard', label: 'Tableau de bord', icon: LayoutDashboard },
    { to: '/evaluations', label: 'Évaluations', icon: Award },
    { to: '/probation', label: 'Probations', icon: ClipboardList },
    { to: '/training/maintenances', label: 'Maintien QF', icon: ShieldCheck },
    { to: '/agents', label: 'Agents', icon: Users },
]

const NAV_MENTOR: NavItem[] = [
    { to: '/dashboard', label: 'Tableau de bord', icon: LayoutDashboard },
    { to: '/mentoring', label: 'Mes mentorats', icon: BookOpen },
    { to: '/reports', label: 'Rapports', icon: FileText },
    { to: '/agents', label: 'Agents', icon: Users },
]

const NAV_INSTRUCTOR: NavItem[] = [
    { to: '/dashboard', label: 'Tableau de bord', icon: LayoutDashboard },
    { to: '/training', label: 'Formations & Cours', icon: GraduationCap },
    { to: '/training/maintenances', label: 'Maintien QF', icon: ShieldCheck },
    { to: '/agents', label: 'Stagiaires', icon: Users },
]

const NAV_AGENT: NavItem[] = [
    { to: '/dashboard', label: 'Mon tableau de bord', icon: LayoutDashboard },
    { to: '/probation', label: 'Ma probation', icon: ClipboardList },
    { to: '/mentoring', label: 'Mon mentorat', icon: BookOpen },
    { to: '/arcep', label: 'Mon carnet ARCEP', icon: BookMarked },
    { to: '/evaluations', label: 'Mes évaluations', icon: Award },
    { to: '/reports', label: 'Mes rapports', icon: FileText },
    { to: '/training', label: 'Formations', icon: GraduationCap },
]

// ─── Helpers ──────────────────────────────────────────────────────────────────

function detectRole(user: User | null): string {
    const roles: string[] = user?.roles ?? []
    if (user?.is_superuser || user?.is_admin || roles.includes('ADMIN')) return 'admin'
    if (roles.includes('UNIT_CHIEF')) return 'unit_chief'
    if (roles.includes('APPROVER')) return 'approver'
    if (roles.includes('EVALUATOR')) return 'evaluator'
    if (roles.includes('MENTOR')) return 'mentor'
    if (roles.includes('INSTRUCTOR')) return 'instructor'
    return 'agent'
}

function getNavItems(role: string): NavItem[] {
    switch (role) {
        case 'admin': return NAV_ADMIN
        case 'unit_chief': return NAV_UNIT_CHIEF
        case 'approver': return NAV_APPROVER
        case 'evaluator': return NAV_EVALUATOR
        case 'mentor': return NAV_MENTOR
        case 'instructor': return NAV_INSTRUCTOR
        default: return NAV_AGENT
    }
}

const ROLE_LABELS: Record<string, string> = {
    admin: 'Administrateur',
    unit_chief: "Chef d'unité",
    approver: 'Approbateur',
    evaluator: 'Évaluateur',
    mentor: 'Mentor',
    instructor: 'Instructeur',
    agent: 'Agent',
}

/**
 * Une teinte distincte par role : la pastille du menu lateral est le seul
 * repere permanent du role avec lequel on est connecte.
 *
 * Approbateur et mentor se sont retrouves de la meme couleur lors de la
 * refonte de la palette — l'un etait indigo, l'autre bleu, deux familles
 * fusionnees depuis en `info`. Le mentor passe au vert, qui restait libre.
 */
const ROLE_COLORS: Record<string, string> = {
    admin: 'bg-danger-500/20 text-danger-300',
    unit_chief: 'bg-asecna-500/20 text-asecna-300',
    approver: 'bg-info-500/20 text-info-300',
    evaluator: 'bg-warning-500/20 text-warning-300',
    mentor: 'bg-success-500/20 text-success-300',
    instructor: 'bg-accent-500/20 text-accent-300',
    agent: 'bg-gray-500/20 text-gray-300',
}

// ─── Composant Layout ────────────────────────────────────────────────────────

export default function Layout() {
    const { user, logout, updateUser } = useAuth()
    const navigate = useNavigate()
    const location = useLocation()
    const [sidebarOpen, setSidebarOpen] = useState(true)
    const fileInputRef = useRef<HTMLInputElement>(null)
    const [isUploading, setIsUploading] = useState(false)

    const handlePhotoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (!file) return

        setIsUploading(true)
        const formData = new FormData()
        formData.append('photo', file)

        try {
            const res = await authApi.updateMe(formData)
            updateUser({ photo: res.data.photo })
        } catch (error) {
            console.error("Erreur upload photo", error)
            alert("Erreur lors de la mise à jour de la photo.")
        } finally {
            setIsUploading(false)
            if (fileInputRef.current) {
                fileInputRef.current.value = ''
            }
        }
    }

    const role = detectRole(user)
    const navItems = getNavItems(role)

    const handleLogout = () => {
        logout()
        navigate('/login')
    }

    // Trouver le label de la page actuelle
    const currentPage = navItems.find(item => item.to === location.pathname)
        ?? navItems.find(item => item.to !== '/' && location.pathname.startsWith(item.to + '/'))

    const initials = user ? `${user.first_name?.[0] ?? ''}${user.last_name?.[0] ?? ''}`.toUpperCase() : 'U'

    return (
        <div className="flex h-screen bg-gray-50 overflow-hidden">
            {/* ── Sidebar ──────────────────────────────────────────────── */}
            <aside className={`${sidebarOpen ? 'w-60' : 'w-16'} bg-gray-900 text-white flex flex-col transition-all duration-300 flex-shrink-0`}>
                {/* Logo */}
                <div className="h-16 flex items-center px-4 border-b border-gray-800">
                    {sidebarOpen ? (
                        <div className="flex items-center gap-3 min-w-0">
                            <div className="w-8 h-8 rounded-lg overflow-hidden bg-asecna-700 flex-shrink-0 flex items-center justify-center">
                                <img src="/asecna_logo.png" alt="ASECNA" className="w-full h-full object-cover"
                                    onError={e => { (e.target as HTMLImageElement).style.display = 'none' }} />
                                <span className="text-white font-bold text-sm">A</span>
                            </div>
                            <div className="min-w-0">
                                <div className="font-bold text-sm text-white">ASECNA</div>
                                <div className="text-xs text-gray-500 truncate">Career Management</div>
                            </div>
                        </div>
                    ) : (
                        <div className="w-8 h-8 rounded-lg bg-asecna-700 flex items-center justify-center mx-auto overflow-hidden">
                            <img src="/asecna_logo.png" alt="A" className="w-full h-full object-cover"
                                onError={e => { (e.target as HTMLImageElement).style.display = 'none' }} />
                            <span className="text-white font-bold text-sm">A</span>
                        </div>
                    )}
                </div>

                {/* Badge rôle */}
                {sidebarOpen && (
                    <div className="px-4 pt-3 pb-1">
                        <span className={`inline-block text-xs font-medium px-2 py-0.5 rounded-full ${ROLE_COLORS[role]}`}>
                            {ROLE_LABELS[role]}
                        </span>
                    </div>
                )}

                {/* Navigation */}
                <nav className="flex-1 py-2 overflow-y-auto overflow-x-hidden">
                    {navItems.map(({ to, label, icon: Icon }) => (
                        <NavLink
                            key={to}
                            to={to}
                            end
                            className={({ isActive }) =>
                                `flex items-center gap-3 px-3 py-2.5 mx-2 rounded-lg mb-0.5 text-sm transition-all duration-150 ${isActive
                                    ? 'bg-asecna-600 text-white shadow-sm'
                                    : 'text-gray-400 hover:bg-gray-800 hover:text-gray-100'
                                }`
                            }
                            title={!sidebarOpen ? label : undefined}
                        >
                            <Icon size={17} className="flex-shrink-0" />
                            {sidebarOpen && <span className="truncate">{label}</span>}
                        </NavLink>
                    ))}
                </nav>

                {/* Profil + déconnexion */}
                <div className="border-t border-gray-800 p-3">
                    {sidebarOpen && user && (
                        <div className="flex items-center gap-3 px-2 py-2 mb-1 rounded-lg bg-gray-800/50">
                            <button
                                onClick={() => fileInputRef.current?.click()}
                                disabled={isUploading}
                                className="w-8 h-8 rounded-full bg-asecna-600 flex items-center justify-center text-white text-sm font-extrabold flex-shrink-0 overflow-hidden cursor-pointer hover:opacity-80 transition-opacity disabled:opacity-50 border-none outline-none"
                                title="Changer la photo de profil"
                            >
                                {user?.photo
                                    ? <img src={user.photo} alt="avatar" className="w-full h-full object-cover" />
                                    : <span className="select-none">{initials}</span>
                                }
                            </button>
                            <div className="min-w-0">
                                <div className="text-xs font-semibold text-white truncate leading-tight">
                                    {user.first_name} {user.last_name}
                                </div>
                                <div className="text-xs text-gray-400 truncate">{ROLE_LABELS[role]}</div>
                            </div>
                        </div>
                    )}
                    <button
                        onClick={handleLogout}
                        className="flex items-center gap-3 px-3 py-2 text-gray-500 hover:text-danger-400 hover:bg-danger-950/30 rounded-lg w-full text-sm transition-colors"
                        title="Déconnexion"
                    >
                        <LogOut size={16} className="flex-shrink-0" />
                        {sidebarOpen && 'Déconnexion'}
                    </button>
                </div>
            </aside>

            {/* ── Zone principale ────────────────────────────────────── */}
            <div className="flex-1 flex flex-col overflow-hidden">

                {/* Topbar professionnelle */}
                <header className="h-16 bg-white border-b border-gray-100 flex items-center px-6 gap-4 flex-shrink-0 shadow-sm">
                    {/* Bouton toggle sidebar */}
                    <button
                        onClick={() => setSidebarOpen(!sidebarOpen)}
                        className="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors"
                    >
                        {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
                    </button>

                    {/* Fil d'ariane */}
                    <div className="flex items-center gap-2 text-sm">
                        <span className="text-gray-400 hidden sm:block">ASECNA</span>
                        <span className="text-gray-300 hidden sm:block">/</span>
                        <span className="font-semibold text-gray-700">{currentPage?.label ?? 'Tableau de bord'}</span>
                    </div>

                    {/* Spacer */}
                    <div className="flex-1" />

                    {/* Date */}
                    <span className="text-xs text-gray-400 hidden md:block">
                        {new Date().toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
                    </span>

                    {/* Notifications (visuel) */}
                    <button className="w-9 h-9 flex items-center justify-center rounded-xl text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors relative">
                        <Bell size={18} />
                        <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-asecna-500 rounded-full" />
                    </button>

                    {/* Avatar utilisateur */}
                    <div className="flex items-center gap-2.5 pl-2 border-l border-gray-100">
                        <input 
                            type="file" 
                            ref={fileInputRef} 
                            onChange={handlePhotoUpload} 
                            accept="image/*" 
                            className="hidden" 
                        />
                        <button
                            onClick={() => fileInputRef.current?.click()}
                            disabled={isUploading}
                            className="w-9 h-9 rounded-xl bg-asecna-600 flex items-center justify-center text-white text-base font-extrabold overflow-hidden cursor-pointer hover:opacity-80 transition-opacity disabled:opacity-50 border-none outline-none"
                            title="Changer la photo de profil"
                        >
                            {user?.photo
                                ? <img src={user.photo} alt="avatar" className="w-full h-full object-cover" />
                                : <span className="select-none">{initials}</span>
                            }
                        </button>
                        {user && (
                            <div className="hidden lg:block leading-tight">
                                <div className="text-sm font-semibold text-gray-800">{user.first_name} {user.last_name}</div>
                                <div className="text-xs text-gray-400">{ROLE_LABELS[role]}</div>
                            </div>
                        )}
                        {/* Accès à « Mon profil » : c'est le seul endroit d'où un
                            agent peut changer son mot de passe. */}
                        <NavLink
                            to="/profile"
                            title="Mon profil et mon mot de passe"
                            className={({ isActive }) =>
                                `p-2 rounded-lg transition-colors ${isActive
                                    ? 'text-asecna-600 bg-asecna-50'
                                    : 'text-gray-400 hover:text-gray-700 hover:bg-gray-100'}`
                            }
                        >
                            <UserCircle size={18} />
                        </NavLink>
                    </div>
                </header>

                {/* Contenu de la page */}
                <main className="flex-1 overflow-y-auto p-6">
                    <Outlet />
                </main>
            </div>
        </div>
    )
}
