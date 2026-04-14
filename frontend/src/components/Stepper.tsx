export function Stepper() {
  return (
    <div className="stepper">
      <div className="step step-active">
        <span>1</span>
        <strong>Kanal Linklerini Gir</strong>
      </div>
      <div className="step-divider" />
      <div className="step">
        <span>2</span>
        <strong>Tweetleri Cek ve Eslestir</strong>
      </div>
      <div className="step-divider" />
      <div className="step">
        <span>3</span>
        <strong>Yorumlari Cek ve Gor</strong>
      </div>
    </div>
  )
}
