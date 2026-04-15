type SidebarProps = {
  tweetsPerChannel: number
  setTweetsPerChannel: (value: number) => void
  minChannelsForMatch: number
  setMinChannelsForMatch: (value: number) => void
  replyCount: number
  setReplyCount: (value: number) => void
  twitterAuthToken: string
  setTwitterAuthToken: (value: string) => void
  twitterCt0: string
  setTwitterCt0: (value: string) => void
  twitterBearerToken: string
  setTwitterBearerToken: (value: string) => void
}

export function Sidebar({
  tweetsPerChannel,
  setTweetsPerChannel,
  minChannelsForMatch,
  setMinChannelsForMatch,
  replyCount,
  setReplyCount,
  twitterAuthToken,
  setTwitterAuthToken,
  twitterCt0,
  setTwitterCt0,
  twitterBearerToken,
  setTwitterBearerToken,
}: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="brand-block">
        <h1>Twitter Haber Analizi</h1>
        <p>Kontrol Paneli</p>
      </div>

      <div className="sidebar-panels">
        <section className="sidebar-panel">
          <h2>Ayarlar</h2>
          <div className="control-grid control-grid-three">
            <div className="control-block">
              <label>Kanal başına tweet sayısı</label>
              <input
                type="number"
                min="1"
                max="50"
                value={tweetsPerChannel}
                onChange={(event) => setTweetsPerChannel(Number(event.target.value) || 10)}
              />
            </div>
            <div className="control-block">
              <label>Ortak haber eşiği</label>
              <input
                type="number"
                min="2"
                max="10"
                value={minChannelsForMatch}
                onChange={(event) => setMinChannelsForMatch(Number(event.target.value) || 2)}
              />
            </div>
            <div className="control-block">
              <label>Tweet başına yorum sayısı</label>
              <input
                type="number"
                min="1"
                max="100"
                value={replyCount}
                onChange={(event) => setReplyCount(Number(event.target.value) || 20)}
              />
            </div>
          </div>
        </section>

        <section className="sidebar-panel">
          <h2>Kimlik Bilgileri</h2>
          <div className="control-grid control-grid-three">
            <div className="control-block">
              <label>Twitter auth_token</label>
              <input
                type="password"
                value={twitterAuthToken}
                onChange={(event) => setTwitterAuthToken(event.target.value)}
                placeholder="auth_token"
              />
            </div>
            <div className="control-block">
              <label>Twitter ct0</label>
              <input
                type="password"
                value={twitterCt0}
                onChange={(event) => setTwitterCt0(event.target.value)}
                placeholder="ct0"
              />
            </div>
            <div className="control-block">
              <label>Bearer Token</label>
              <input
                type="password"
                value={twitterBearerToken}
                onChange={(event) => setTwitterBearerToken(event.target.value)}
                placeholder="Bearer ..."
              />
            </div>
          </div>
        </section>
        </div>
    </aside>
  )
}
