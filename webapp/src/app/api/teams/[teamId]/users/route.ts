import { NextRequest, NextResponse } from 'next/server'
import { supabaseAdmin } from '@/lib/supabase'

// GET /api/teams/[teamId]/users - Lister les utilisateurs d'une équipe
export async function GET(
  request: NextRequest,
  { params }: { params: { teamId: string } }
) {
  try {
    const { data: users, error } = await supabaseAdmin
      .from('users')
      .select('*')
      .eq('team_id', params.teamId)
      .order('created_at', { ascending: false })

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 500 })
    }

    return NextResponse.json({ users })
  } catch (error) {
    return NextResponse.json({ error: 'Erreur serveur' }, { status: 500 })
  }
}

// POST /api/teams/[teamId]/users - Ajouter un utilisateur à une équipe
export async function POST(
  request: NextRequest,
  { params }: { params: { teamId: string } }
) {
  try {
    const { email, name, role = 'member' } = await request.json()

    if (!email || !name) {
      return NextResponse.json({ 
        error: 'L\'email et le nom sont requis' 
      }, { status: 400 })
    }

    // Vérifier que l'équipe existe
    const { data: team, error: teamError } = await supabaseAdmin
      .from('teams')
      .select('id')
      .eq('id', params.teamId)
      .single()

    if (teamError || !team) {
      return NextResponse.json({ error: 'Équipe non trouvée' }, { status: 404 })
    }

    // Vérifier que l'email n'est pas déjà utilisé
    const { data: existingUser } = await supabaseAdmin
      .from('users')
      .select('id')
      .eq('email', email)
      .single()

    if (existingUser) {
      return NextResponse.json({ 
        error: 'Un utilisateur avec cet email existe déjà' 
      }, { status: 409 })
    }

    const { data: user, error } = await supabaseAdmin
      .from('users')
      .insert([{
        email,
        name,
        team_id: params.teamId,
        role
      }])
      .select()
      .single()

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 500 })
    }

    return NextResponse.json({ user }, { status: 201 })
  } catch (error) {
    return NextResponse.json({ error: 'Erreur serveur' }, { status: 500 })
  }
}
