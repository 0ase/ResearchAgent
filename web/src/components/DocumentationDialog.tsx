import { Dialog } from './Dialog'
import { PixelIcon } from './PixelIcon'
import { projectGitHub } from '../data/homepage'

export function DocumentationDialog({ open, onClose, onWorkspace }: { open: boolean; onClose: () => void; onWorkspace: () => void }) {
  return <Dialog open={open} onClose={onClose} labelId="documentation-heading" className="documentation-dialog">
    <div className="dialog-heading"><h2 id="documentation-heading">使用文档</h2><button className="icon-button" onClick={onClose} aria-label="关闭文档"><PixelIcon name="close" /></button></div>
    <section><h3>从研究问题开始</h3><p>在首页输入你希望研究的问题，点击“开始研究”进入工作台。输入为空时直接进入对话页面，不创建研究任务。Enter 提交，Shift + Enter 换行。问题最多 2000 字。</p></section>
    <section><h3>查看过程与证据</h3><p>研究过程记录问题拆解、检索、筛选、阅读与分析。完成后过程折叠保留；报告中的引用可以打开对应文献，综述可导出为 Markdown。</p></section>
    <section><h3>设置与历史</h3><p>“设置”可调整下一次研究的目标阅读数量与本机模型配置。保存配置后需重启后端。进入工作台后，可从左侧研究记录恢复历史；点击左上角 B1GONE 标志返回首页。</p></section>
    <p><a href={`${projectGitHub}#readme`} target="_blank" rel="noopener noreferrer">查看项目说明与启动方法<PixelIcon name="external" /></a></p>
    <button className="key-button dialog-done" onClick={onWorkspace}>进入研究工作台</button>
  </Dialog>
}
