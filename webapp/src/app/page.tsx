'use client'

import { useState, useEffect } from 'react'
import { Team, User } from '@/lib/supabase'

export default function Home() {
  const [teams, setTeams] = useState<Team[]>([])
  const [selectedTeam, setSelectedTeam] = useState<Team | null>(null)
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [newTeamName, setNewTeamName] = useState('')
  const [newUserEmail, setNewUserEmail] = useState('')
  const [newUserName, setNewUserName] = useState('')

  // Charger les équipes au démarrage
  useEffect(() => {
    loadTeams()
  }, [])

  // Charger les utilisateurs quand une équipe est sélectionnée
  useEffect(() => {
    if (selectedTeam) {
      loadUsers(selectedTeam.id)
    }
  }, [selectedTeam])

  const loadTeams = async () => {
    try {
      const response = await fetch('/api/teams')
      const data = await response.json()
      setTeams(data.teams || [])
    } catch (error) {
      console.error('Erreur lors du chargement des équipes:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadUsers = async (teamId: string) => {
    try {
      const response = await fetch(`/api/teams/${teamId}/users`)
      const data = await response.json()
      setUsers(data.users || [])
    } catch (error) {
      console.error('Erreur lors du chargement des utilisateurs:', error)
    }
  }

  const createTeam = async () => {
    if (!newTeamName.trim()) return

    try {
      const response = await fetch('/api/teams', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newTeamName })
      })

      if (response.ok) {
        setNewTeamName('')
        loadTeams()
      } else {
        const error = await response.json()
        alert(`Erreur: ${error.error}`)
      }
    } catch (error) {
      console.error('Erreur lors de la création de l\'équipe:', error)
    }
  }

  const addUser = async () => {
    if (!selectedTeam || !newUserEmail.trim() || !newUserName.trim()) return

    try {
      const response = await fetch(`/api/teams/${selectedTeam.id}/users`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          email: newUserEmail, 
          name: newUserName 
        })
      })

      if (response.ok) {
        setNewUserEmail('')
        setNewUserName('')
        loadUsers(selectedTeam.id)
      } else {
        const error = await response.json()
        alert(`Erreur: ${error.error}`)
      }
    } catch (error) {
      console.error('Erreur lors de l\'ajout de l\'utilisateur:', error)
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    alert('Token copié dans le presse-papiers!')
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-xl">Chargement...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-white">
      <div className="max-w-6xl mx-auto py-8 px-4">
        <div className="text-center mb-12">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Collective Brain
          </h1>
          <p className="text-lg text-gray-600">
            Gestion des équipes - Mémoire collective multi-tenant
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Section Équipes */}
          <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">
              Équipes
            </h2>
            
            {/* Créer une nouvelle équipe */}
            <div className="mb-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
              <h3 className="font-medium text-gray-900 mb-3">Créer une nouvelle équipe</h3>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Nom de l'équipe"
                  value={newTeamName}
                  onChange={(e) => setNewTeamName(e.target.value)}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
                <button
                  onClick={createTeam}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
                >
                  Créer
                </button>
              </div>
            </div>

            {/* Liste des équipes */}
            <div className="space-y-3">
              {teams.map((team) => (
                <div
                  key={team.id}
                  className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                    selectedTeam?.id === team.id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                  }`}
                  onClick={() => setSelectedTeam(team)}
                >
                  <div className="font-medium text-gray-900 mb-2">{team.name}</div>
                  <div className="text-sm text-gray-600 flex items-center">
                    <span className="font-mono bg-gray-100 px-2 py-1 rounded text-xs border">
                      {team.team_token}
                    </span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        copyToClipboard(team.team_token)
                      }}
                      className="ml-2 p-1 hover:bg-gray-200 rounded transition-colors"
                      title="Copier le token"
                    >
                      <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Section Utilisateurs */}
          <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">
              Utilisateurs {selectedTeam ? `- ${selectedTeam.name}` : ''}
            </h2>

            {selectedTeam ? (
              <>
                {/* Ajouter un utilisateur */}
                <div className="mb-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
                  <h3 className="font-medium text-gray-900 mb-3">Ajouter un utilisateur</h3>
                  <div className="space-y-3">
                    <input
                      type="email"
                      placeholder="Email"
                      value={newUserEmail}
                      onChange={(e) => setNewUserEmail(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
                    />
                    <input
                      type="text"
                      placeholder="Nom"
                      value={newUserName}
                      onChange={(e) => setNewUserName(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
                    />
                    <button
                      onClick={addUser}
                      className="w-full px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 transition-colors"
                    >
                      Ajouter
                    </button>
                  </div>
                </div>

                {/* Liste des utilisateurs */}
                <div className="space-y-3">
                  {users.map((user) => (
                    <div key={user.id} className="p-4 border border-gray-200 rounded-lg bg-gray-50">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <div className="font-medium text-gray-900 mb-1">{user.name}</div>
                          <div className="text-sm text-gray-600 mb-2">{user.email}</div>
                          <div className="text-sm text-gray-600 flex items-center">
                            <span className="font-mono bg-gray-100 px-2 py-1 rounded text-xs border">
                              {user.user_token}
                            </span>
                            <button
                              onClick={() => copyToClipboard(user.user_token)}
                              className="ml-2 p-1 hover:bg-gray-200 rounded transition-colors"
                              title="Copier le token"
                            >
                              <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                              </svg>
                            </button>
                          </div>
                        </div>
                        <span className={`px-2 py-1 text-xs rounded-full font-medium ${
                          user.role === 'admin' 
                            ? 'bg-red-100 text-red-800 border border-red-200' 
                            : 'bg-gray-100 text-gray-800 border border-gray-200'
                        }`}>
                          {user.role === 'admin' ? 'Admin' : 'Membre'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="text-gray-500 text-center py-12">
                <div className="text-4xl mb-4">👆</div>
                <p className="text-lg">Sélectionnez une équipe pour voir ses utilisateurs</p>
              </div>
            )}
          </div>
        </div>

        {/* Instructions */}
        <div className="mt-8 bg-gray-50 border border-gray-200 rounded-lg p-6">
          <h3 className="font-semibold text-gray-900 mb-4 text-lg">Instructions d'utilisation</h3>
          <div className="text-gray-700 space-y-3">
            <div className="flex items-start">
              <span className="bg-blue-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-medium mr-3 mt-0.5">1</span>
              <p><strong className="text-gray-900">Créez une équipe</strong> et copiez son token d'équipe</p>
            </div>
            <div className="flex items-start">
              <span className="bg-blue-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-medium mr-3 mt-0.5">2</span>
              <p><strong className="text-gray-900">Ajoutez des utilisateurs</strong> à l'équipe et copiez leurs tokens utilisateur</p>
            </div>
            <div className="flex items-start">
              <span className="bg-blue-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-medium mr-3 mt-0.5">3</span>
              <p><strong className="text-gray-900">Dans Le Chat</strong>, utilisez le token utilisateur pour accéder à la mémoire collective de l'équipe</p>
            </div>
            <div className="flex items-start">
              <span className="bg-blue-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-medium mr-3 mt-0.5">4</span>
              <p><strong className="text-gray-900">Chaque équipe</strong> a sa propre collection de mémoires isolée</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}