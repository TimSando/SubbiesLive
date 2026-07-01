import React from 'react'
import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import userEvent from '@testing-library/user-event'
import Layout from './Layout'

function renderLayout(initialPath = '/') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Layout />
    </MemoryRouter>
  )
}

describe('Layout component navigation structures', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
  })

  it('renders brand logo and title linking to home', () => {
    renderLayout()
    const brandLink = screen.getByRole('link', { name: /🏉 SubbiesStats/i })
    expect(brandLink).toBeInTheDocument()
    expect(brandLink).toHaveAttribute('href', '/')
  })

  it('renders links in the desktop nav container', () => {
    renderLayout()
    const desktopNav = document.querySelector('.nav__desktop-links')
    expect(desktopNav).toBeInTheDocument()

    const homeLink = screen.getAllByRole('link', { name: /home/i }).find(
      el => el.closest('.nav__desktop-links')
    )
    const clubsLink = screen.getAllByRole('link', { name: /clubs/i }).find(
      el => el.closest('.nav__desktop-links')
    )
    const compsLink = screen.getAllByRole('link', { name: /competitions/i }).find(
      el => el.closest('.nav__desktop-links')
    )
    const statsLink = screen.getAllByRole('link', { name: /stats/i }).find(
      el => el.closest('.nav__desktop-links')
    )
    const refZoneLink = screen.getAllByRole('link', { name: /refzone/i }).find(
      el => el.closest('.nav__desktop-links')
    )
    const notifLink = screen.getAllByRole('link', { name: /notifications/i }).find(
      el => el.closest('.nav__desktop-links')
    )
    expect(homeLink).toHaveAttribute('href', '/')
    expect(clubsLink).toHaveAttribute('href', '/clubs')
    expect(compsLink).toHaveAttribute('href', '/competitions')
    expect(statsLink).toHaveAttribute('href', '/stats')
    expect(refZoneLink).toHaveAttribute('href', '/refzone')
    expect(notifLink).toHaveAttribute('href', '/notifications')
  })

  it('renders primary links in the mobile bottom tab bar', () => {
    renderLayout()
    const bottomBar = document.querySelector('.nav-bottom-bar')
    expect(bottomBar).toBeInTheDocument()

    const homeLink = screen.getAllByRole('link', { name: /home/i }).find(
      el => el.closest('.nav-bottom-bar')
    )
    const clubsLink = screen.getAllByRole('link', { name: /clubs/i }).find(
      el => el.closest('.nav-bottom-bar')
    )
    const compsLink = screen.getAllByRole('link', { name: /competitions/i }).find(
      el => el.closest('.nav-bottom-bar')
    )
    const statsLink = screen.getAllByRole('link', { name: /stats/i }).find(
      el => el.closest('.nav-bottom-bar')
    )

    expect(homeLink).toHaveAttribute('href', '/')
    expect(clubsLink).toHaveAttribute('href', '/clubs')
    expect(compsLink).toHaveAttribute('href', '/competitions')
    expect(statsLink).toHaveAttribute('href', '/stats')
  })

  it('renders correct sections in the side drawer', () => {
    renderLayout()
    const drawer = document.querySelector('.nav__drawer')
    expect(drawer).toBeInTheDocument()

    // Assert tools and settings title exists
    expect(screen.getByText('Tools & Settings')).toBeInTheDocument()

    // Find links specifically inside drawer
    const refZoneLink = screen.getAllByRole('link', { name: /refzone/i }).find(
      el => el.closest('.nav__drawer')
    )
    const notifLink = screen.getAllByRole('link', { name: /notifications/i }).find(
      el => el.closest('.nav__drawer')
    )
    expect(refZoneLink).toHaveAttribute('href', '/refzone')
    expect(notifLink).toHaveAttribute('href', '/notifications')
  })

  it('toggles mobile drawer open and closed', async () => {
    renderLayout()
    const burgerButton = screen.getByRole('button', { name: /toggle navigation menu/i })
    const drawer = document.querySelector('.nav__drawer')
    const backdrop = document.querySelector('.nav__drawer-backdrop')

    // Initially closed
    expect(drawer).not.toHaveClass('nav__drawer--open')
    expect(backdrop).not.toHaveClass('nav__drawer-backdrop--open')

    // Click burger to open
    await userEvent.click(burgerButton)
    expect(drawer).toHaveClass('nav__drawer--open')
    expect(backdrop).toHaveClass('nav__drawer-backdrop--open')

    // Click backdrop to close
    await userEvent.click(backdrop)
    expect(drawer).not.toHaveClass('nav__drawer--open')
    expect(backdrop).not.toHaveClass('nav__drawer-backdrop--open')
  })


})
