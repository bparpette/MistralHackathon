import { NextRequest, NextResponse } from 'next/server'
import { supabaseAdmin, UserTokenInfo } from '@/lib/supabase'

// POST /api/auth/verify - Vérifier un token utilisateur (utilisé par le MCP)
export async function POST(request: NextRequest) {
  try {
    const { user_token } = await request.json()

    if (!user_token) {
      return NextResponse.json({ 
        error: 'Token utilisateur requis' 
      }, { status: 400 })
    }

    // Utiliser la fonction SQL pour vérifier le token
    const { data, error } = await supabaseAdmin
      .rpc('verify_user_token', { token: user_token })

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 500 })
    }

    if (!data || data.length === 0) {
      return NextResponse.json({ 
        error: 'Token invalide' 
      }, { status: 401 })
    }

    const userInfo: UserTokenInfo = data[0]

    return NextResponse.json({
      valid: true,
      user: userInfo
    })
  } catch (error) {
    return NextResponse.json({ error: 'Erreur serveur' }, { status: 500 })
  }
}
