import { useQuery, useQueryClient } from '@tanstack/react-query'
import { trainingApi, agentsApi } from '../../api'
import { useAuth } from '../../store/authContextValue'
import {
    GraduationCap, BookOpen, Plus, X, Users,
    Clock, Target, BookCheck, FileText, Eye, EyeOff, Trash2,
} from 'lucide-react'
import { useState } from 'react'
import { apiErrorMessage } from '../../api/client'
import type { User, Internship, Training, Course, Specialty } from '../../types'
import { hasAnyRole, hasRole } from '../../utils/roles'

const TYPE_LABELS: Record<string, string> = {
    QUALIFYING: 'Qualification', CONTINUING: 'Formation continue',
    REFRESHER: 'Recyclage', INITIAL: 'Formation initiale',
}
const TYPE_COLORS: Record<string, string> = {
    QUALIFYING: 'bg-asecna-100 text-asecna-700', CONTINUING: 'bg-info-100 text-info-700',
    REFRESHER: 'bg-warning-100 text-warning-700', INITIAL: 'bg-accent-100 text-accent-700',
}

const canCreate = (user: User | null) => hasAnyRole(user, 'INSTRUCTOR', 'UNIT_CHIEF')

/**
 * Seul un INSTRUCTEUR (ou un admin) dépose et publie un cours : c'est la
 * règle de `CourseViewSet.get_permissions` côté serveur. Un chef d'unité
 * recevrait un 403.
 */
const canManageCourses = (user: User | null) => hasRole(user, 'INSTRUCTOR')

export default function TrainingPage() {
    const { user } = useAuth()
    const qc = useQueryClient()
    const [activeTab, setActiveTab] = useState<'trainings' | 'courses' | 'internships'>('trainings')
    const [showCreateInternship, setShowCreateInternship] = useState(false)
    const [showCreateCourse, setShowCreateCourse] = useState(false)
    const [flash, setFlash] = useState<{ text: string; ok: boolean } | null>(null)
    const [internForm, setInternForm] = useState({ agent: '', training: '', start_date: '', end_date: '' })
    const [courseForm, setCourseForm] = useState({ title: '', training: '', content: '', order: 0 })

    const notify = (text: string, ok = true) => {
        setFlash({ text, ok })
        setTimeout(() => setFlash(null), 4000)
    }

    const { data: specialtiesData } = useQuery({
        queryKey: ['specialties'],
        queryFn: () => trainingApi.specialties().then(r => r.data),
    })
    const { data: trainingsData, isLoading: loadingT } = useQuery({
        queryKey: ['trainings'],
        queryFn: () => trainingApi.trainings().then(r => r.data),
    })
    const { data: internshipsData, isLoading: loadingI } = useQuery({
        queryKey: ['internships'],
        queryFn: () => trainingApi.internships().then(r => r.data),
    })
    const { data: agentsData } = useQuery({
        queryKey: ['agents-select-training'],
        queryFn: () => agentsApi.list().then(r => r.data),
        enabled: showCreateInternship,
    })
    // Cours e-learning. Le backend filtre déjà par rôle : un agent ne reçoit
    // que les cours publiés, un instructeur voit aussi ses brouillons.
    const { data: coursesData, isLoading: loadingC } = useQuery({
        queryKey: ['courses'],
        queryFn: () => trainingApi.courses().then(r => r.data),
    })

    const courses = coursesData?.results ?? []
    const specialties = specialtiesData?.results ?? []
    const trainings = trainingsData?.results ?? []
    const internships = internshipsData?.results ?? []
    const agents = agentsData?.results ?? []

    const activeInternships = internships.filter((i: Internship) => !i.is_passed)
    const passedInternships = internships.filter((i: Internship) => i.is_passed)

    const refreshCourses = () => qc.invalidateQueries({ queryKey: ['courses'] })

    const handleCreateCourse = async (e: React.FormEvent) => {
        e.preventDefault()
        try {
            // `instructor` est imposé côté serveur (utilisateur connecté) et
            // `is_published` vaut false : un cours naît en brouillon.
            await trainingApi.createCourse({
                title: courseForm.title,
                training: Number(courseForm.training),
                content: courseForm.content,
                order: Number(courseForm.order) || 0,
            })
            refreshCourses()
            setShowCreateCourse(false)
            setCourseForm({ title: '', training: '', content: '', order: 0 })
            notify('Cours créé — il reste en brouillon tant qu\'il n\'est pas publié.')
        } catch (err: unknown) {
            notify(apiErrorMessage(err, 'Création du cours impossible.'), false)
        }
    }

    const togglePublish = async (course: Course) => {
        try {
            if (course.is_published) {
                await trainingApi.unpublishCourse(course.id)
                notify('Cours dépublié — il disparaît de la vue des agents.')
            } else {
                await trainingApi.publishCourse(course.id)
                notify('Cours publié — il est visible des agents.')
            }
            refreshCourses()
        } catch (err: unknown) {
            notify(apiErrorMessage(err, 'Opération impossible.'), false)
        }
    }

    const removeCourse = async (course: Course) => {
        try {
            await trainingApi.deleteCourse(course.id)
            refreshCourses()
            notify('Cours supprimé.')
        } catch (err: unknown) {
            notify(apiErrorMessage(err, 'Suppression impossible.'), false)
        }
    }

    const handleCreateInternship = async (e: React.FormEvent) => {
        e.preventDefault()
        try {
            // L'import dynamique de `api/client` annulait le decoupage du
            // bundle : le module est deja importe statiquement par ailleurs,
            // Vite emettait un avertissement et gardait tout dans le meme
            // morceau. On passe par la couche `api`, comme les autres ecrans.
            await trainingApi.createInternship({
                agent: Number(internForm.agent),
                training: Number(internForm.training),
                start_date: internForm.start_date,
                end_date: internForm.end_date,
            })
            qc.invalidateQueries({ queryKey: ['internships'] })
            setShowCreateInternship(false)
            setInternForm({ agent: '', training: '', start_date: '', end_date: '' })
            notify('✅ Stage créé avec succès')
        } catch (err: unknown) {
            notify(apiErrorMessage(err, '❌ Erreur'), false)
        }
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                        <GraduationCap size={24} className="text-accent-600" /> Formations & Stages
                    </h1>
                    <p className="text-gray-400 text-sm mt-0.5">
                        {trainingsData?.count ?? 0} formations · {internshipsData?.count ?? 0} stages
                    </p>
                </div>
                {canCreate(user) && (
                    <button onClick={() => setShowCreateInternship(true)}
                        className="flex items-center gap-2 px-4 py-2 bg-accent-600 hover:bg-accent-700 text-white rounded-xl text-sm font-medium transition-colors">
                        <Plus size={16} /> Inscrire à un stage
                    </button>
                )}
            </div>

            {flash && (
                <div className={`p-3 rounded-xl text-sm border ${flash.ok ? 'bg-success-50 border-success-200 text-success-800' : 'bg-danger-50 border-danger-200 text-danger-800'}`}>
                    {flash.text}
                </div>
            )}

            {/* Spécialités */}
            {specialties.length > 0 && (
                <div className="flex flex-wrap gap-2">
                    {specialties.map((s: Specialty) => (
                        <span key={s.id} className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-asecna-50 border border-asecna-100 text-asecna-700 rounded-full text-sm">
                            <span className="font-bold font-mono text-xs">{s.code}</span>
                            <span>{s.name}</span>
                        </span>
                    ))}
                </div>
            )}

            {/* Stats rapides */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="card text-center py-4">
                    <div className="text-2xl font-bold text-accent-600">{trainingsData?.count ?? 0}</div>
                    <div className="text-xs text-gray-500 mt-1">Formations</div>
                </div>
                <div className="card text-center py-4">
                    <div className="text-2xl font-bold text-info-600">{activeInternships.length}</div>
                    <div className="text-xs text-gray-500 mt-1">Stages en cours</div>
                </div>
                <div className="card text-center py-4">
                    <div className="text-2xl font-bold text-success-600">{passedInternships.length}</div>
                    <div className="text-xs text-gray-500 mt-1">Stages réussis</div>
                </div>
                <div className="card text-center py-4">
                    <div className="text-2xl font-bold text-gray-600">
                        {trainings.filter((t: Training) => t.training_type === 'QUALIFYING').length}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">Qualifiantes</div>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 bg-gray-100 p-1 rounded-xl w-fit">
                {([
                    ['trainings', 'Formations', BookOpen],
                    ['courses', 'Cours', FileText],
                    ['internships', 'Stages', Users],
                ] as const).map(([key, label, Icon]) => (
                    <button key={key} onClick={() => setActiveTab(key)}
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${activeTab === key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}>
                        <Icon size={15} /> {label}
                    </button>
                ))}
            </div>

            {/* Onglet Formations */}
            {activeTab === 'trainings' && (
                loadingT ? (
                    <div className="flex items-center justify-center h-40">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent-600" />
                    </div>
                ) : trainings.length === 0 ? (
                    <div className="card text-center py-12 text-gray-400">
                        <BookOpen size={40} className="mx-auto mb-2 opacity-30" />
                        <p>Aucune formation enregistrée</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {trainings.map((t: Training) => (
                            <div key={t.id} className="card hover:shadow-md transition-shadow">
                                <div className="flex items-start justify-between mb-3">
                                    <div className="flex-1">
                                        <h3 className="font-semibold text-gray-900">{t.title}</h3>
                                        <p className="text-xs text-gray-400 mt-0.5">{t.specialty_detail?.name ?? '—'}</p>
                                    </div>
                                    <span className={`badge ml-2 text-xs ${TYPE_COLORS[t.training_type] ?? 'bg-gray-100 text-gray-600'}`}>
                                        {TYPE_LABELS[t.training_type] ?? t.training_type}
                                    </span>
                                </div>
                                {t.description && <p className="text-sm text-gray-600 mb-3 line-clamp-2">{t.description}</p>}
                                <div className="flex flex-wrap gap-3 text-xs text-gray-500 pt-3 border-t border-gray-50">
                                    <span className="flex items-center gap-1"><Clock size={11} /> {t.duration_days}j</span>
                                    <span className="flex items-center gap-1"><Target size={11} /> Seuil {t.passing_score}%</span>
                                    <span className="flex items-center gap-1"><BookCheck size={11} />
                                        {internships.filter((i: Internship) => i.training === t.id).length} stagiaire(s)
                                    </span>
                                    <span className={`ml-auto font-medium ${t.is_active ? 'text-success-600' : 'text-gray-400'}`}>
                                        {t.is_active ? '● Actif' : '○ Inactif'}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                )
            )}

            {/* Onglet Cours */}
            {activeTab === 'courses' && (
                <div className="space-y-4">
                    {canManageCourses(user) && (
                        <div className="flex justify-end">
                            <button
                                onClick={() => setShowCreateCourse(v => !v)}
                                className="flex items-center gap-2 px-4 py-2 bg-accent-600 hover:bg-accent-700 text-white rounded-xl text-sm font-medium transition-colors"
                            >
                                {showCreateCourse ? <X size={16} /> : <Plus size={16} />}
                                {showCreateCourse ? 'Annuler' : 'Nouveau cours'}
                            </button>
                        </div>
                    )}

                    {showCreateCourse && (
                        <form onSubmit={handleCreateCourse} className="card space-y-3">
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                <div className="md:col-span-2">
                                    <label className="block text-xs font-medium text-gray-600 mb-1">Titre *</label>
                                    <input
                                        required value={courseForm.title}
                                        onChange={e => setCourseForm(f => ({ ...f, title: e.target.value }))}
                                        className="w-full border border-gray-200 rounded-xl p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-accent-500"
                                        placeholder="Ex : Phraséologie — module 1"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-medium text-gray-600 mb-1">Formation *</label>
                                    <select
                                        required value={courseForm.training}
                                        onChange={e => setCourseForm(f => ({ ...f, training: e.target.value }))}
                                        className="w-full border border-gray-200 rounded-xl p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-accent-500"
                                    >
                                        <option value="">— Choisir —</option>
                                        {trainings.map((t: Training) => (
                                            <option key={t.id} value={t.id}>{t.title}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-gray-600 mb-1">Contenu *</label>
                                <textarea
                                    required rows={4} value={courseForm.content}
                                    onChange={e => setCourseForm(f => ({ ...f, content: e.target.value }))}
                                    className="w-full border border-gray-200 rounded-xl p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-accent-500"
                                />
                            </div>
                            <button type="submit" className="px-4 py-2 rounded-xl text-sm font-medium bg-accent-600 text-white hover:bg-accent-700">
                                Créer le cours
                            </button>
                        </form>
                    )}

                    {loadingC ? (
                        <div className="flex items-center justify-center h-40">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent-600" />
                        </div>
                    ) : courses.length === 0 ? (
                        <div className="card text-center py-12 text-gray-400">
                            <FileText size={40} className="mx-auto mb-2 opacity-30" />
                            <p>Aucun cours disponible</p>
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {courses.map((c: Course) => (
                                <div key={c.id} className="card flex items-start justify-between gap-4">
                                    <div className="min-w-0">
                                        <div className="flex items-center gap-2 flex-wrap mb-1">
                                            <h3 className="font-semibold text-gray-900">{c.title}</h3>
                                            <span className={`badge text-xs ${c.is_published ? 'bg-success-100 text-success-700' : 'bg-gray-100 text-gray-500'}`}>
                                                {c.is_published ? 'Publié' : 'Brouillon'}
                                            </span>
                                        </div>
                                        <p className="text-xs text-gray-400 mb-2">
                                            {c.training_detail?.title ?? trainings.find((t: Training) => t.id === c.training)?.title ?? '—'}
                                        </p>
                                        <p className="text-sm text-gray-600 line-clamp-2 whitespace-pre-wrap">{c.content}</p>
                                    </div>
                                    {canManageCourses(user) && (
                                        <div className="flex items-center gap-2 shrink-0">
                                            <button
                                                onClick={() => togglePublish(c)}
                                                className={`text-xs px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-colors ${c.is_published
                                                    ? 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                                    : 'bg-success-600 text-white hover:bg-success-700'}`}
                                            >
                                                {c.is_published ? <><EyeOff size={13} /> Dépublier</> : <><Eye size={13} /> Publier</>}
                                            </button>
                                            <button
                                                onClick={() => removeCourse(c)}
                                                title="Supprimer le cours"
                                                className="p-2 rounded-lg text-gray-400 hover:text-danger-600 hover:bg-danger-50"
                                            >
                                                <Trash2 size={15} />
                                            </button>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Onglet Stages */}
            {activeTab === 'internships' && (
                loadingI ? (
                    <div className="flex items-center justify-center h-40">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent-600" />
                    </div>
                ) : internships.length === 0 ? (
                    <div className="card text-center py-12 text-gray-400">
                        <Users size={40} className="mx-auto mb-2 opacity-30" />
                        <p>Aucun stage enregistré</p>
                        {canCreate(user) && (
                            <button onClick={() => setShowCreateInternship(true)}
                                className="mt-3 text-sm text-accent-600 hover:underline">
                                Inscrire un agent →
                            </button>
                        )}
                    </div>
                ) : (
                    <div className="card p-0 overflow-hidden">
                        <table className="w-full text-sm">
                            <thead className="bg-gray-50 border-b border-gray-100">
                                <tr>
                                    {['Agent', 'Formation', 'Début', 'Fin', 'Statut'].map(h => (
                                        <th key={h} className="text-left px-5 py-3 text-gray-500 font-medium text-xs uppercase tracking-wide">{h}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-50">
                                {internships.map((i: Internship) => (
                                    <tr key={i.id} className="hover:bg-gray-50">
                                        <td className="px-5 py-3.5">
                                            <div className="font-medium text-gray-900">{i.agent_detail?.first_name} {i.agent_detail?.last_name}</div>
                                            <div className="text-xs text-gray-400 font-mono">{i.agent_detail?.matricule}</div>
                                        </td>
                                        <td className="px-5 py-3.5 text-gray-600">{i.training_detail?.title ?? '—'}</td>
                                        <td className="px-5 py-3.5 text-gray-500 text-xs">{new Date(i.start_date).toLocaleDateString('fr-FR')}</td>
                                        <td className="px-5 py-3.5 text-gray-500 text-xs">{new Date(i.end_date).toLocaleDateString('fr-FR')}</td>
                                        <td className="px-5 py-3.5">
                                            <span className={`badge text-xs ${i.is_passed ? 'bg-success-100 text-success-700' : 'bg-info-100 text-info-700'}`}>
                                                {i.is_passed ? 'Réussi ✓' : 'En cours'}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )
            )}

            {/* Modal : Inscrire à un stage */}
            {showCreateInternship && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
                    <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-md">
                        <div className="flex items-center justify-between mb-5">
                            <h3 className="text-lg font-bold text-gray-900">Inscrire un agent à un stage</h3>
                            <button onClick={() => setShowCreateInternship(false)} className="p-1 hover:bg-gray-100 rounded-lg">
                                <X size={18} className="text-gray-400" />
                            </button>
                        </div>
                        <form onSubmit={handleCreateInternship} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Agent *</label>
                                <select required value={internForm.agent} onChange={e => setInternForm(f => ({ ...f, agent: e.target.value }))}
                                    className="w-full border border-gray-200 rounded-xl p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-accent-500">
                                    <option value="">— Choisir un agent —</option>
                                    {agents.map((a: User) => (
                                        <option key={a.id} value={a.id}>{a.first_name} {a.last_name} ({a.matricule})</option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Formation *</label>
                                <select required value={internForm.training} onChange={e => setInternForm(f => ({ ...f, training: e.target.value }))}
                                    className="w-full border border-gray-200 rounded-xl p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-accent-500">
                                    <option value="">— Choisir une formation —</option>
                                    {trainings.map((t: Training) => (
                                        <option key={t.id} value={t.id}>{t.title}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Début *</label>
                                    <input required type="date" value={internForm.start_date}
                                        onChange={e => setInternForm(f => ({ ...f, start_date: e.target.value }))}
                                        className="w-full border border-gray-200 rounded-xl p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-accent-500" />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Fin *</label>
                                    <input required type="date" value={internForm.end_date}
                                        onChange={e => setInternForm(f => ({ ...f, end_date: e.target.value }))}
                                        className="w-full border border-gray-200 rounded-xl p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-accent-500" />
                                </div>
                            </div>
                            <div className="flex gap-3 justify-end pt-2">
                                <button type="button" onClick={() => setShowCreateInternship(false)} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-xl">Annuler</button>
                                <button type="submit"
                                    className="px-4 py-2 text-sm font-medium text-white bg-accent-600 hover:bg-accent-700 rounded-xl">
                                    Créer le stage
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    )
}
