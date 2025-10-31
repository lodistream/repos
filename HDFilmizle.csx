// ==CloudStreamScript==
// @name HDFilmizle
// @version 1.0.1
// @description HDFilmizle.to - Türkçe Dublaj ve Altyazılı Film ve Dizi İzle
// @author GitLatte
// @language tr
// @supportedTypes movie, tvseries
// @homepage https://www.hdfilmizle.to
// ==/CloudStreamScript==

import com.lagradost.cloudstream3.*
import com.lagradost.cloudstream3.utils.*
import com.lagradost.cloudstream3.extractors.*
import com.lagradost.cloudstream3.mvvm.safeApiCall
import org.jsoup.nodes.Element

class HDFilmizle : MainAPI() {
    override var mainUrl = "https://www.hdfilmizle.to"
    override var name = "HDFilmizle"
    override val supportedTypes = setOf(TvType.Movie, TvType.TvSeries)
    override var lang = "tr"

    override suspend fun getMainPage(page: Int, request: MainPageRequest): HomePageResponse {
        val items = ArrayList<HomePageList>()
        try {
            val doc = app.get(mainUrl).document
            val popular = doc.select("div.tab-pane.active div.item, div.movie-item").mapNotNull { it.toSearchResult() }
            if (popular.isNotEmpty()) items.add(HomePageList("Popüler Filmler", popular))
            val newMovies = app.get("$mainUrl/film-izle").document.select("div.movie-poster, div.movie-item").mapNotNull { it.toSearchResult() }
            if (newMovies.isNotEmpty()) items.add(HomePageList("Yeni Filmler", newMovies))
            val newSeries = app.get("$mainUrl/dizi-izle").document.select("div.movie-poster, div.movie-item").mapNotNull { it.toSearchResult() }
            if (newSeries.isNotEmpty()) items.add(HomePageList("Popüler Diziler", newSeries))
        } catch (e: Exception) { e.printStackTrace() }
        return HomePageResponse(items)
    }

    override suspend fun search(query: String): List<SearchResponse> {
        return safeApiCall {
            val encoded = java.net.URLEncoder.encode(query, "UTF-8")
            val doc = app.get("$mainUrl/ara?q=$encoded").document
            doc.select("div.movie-item, div.movie-poster, div.item").mapNotNull { it.toSearchResult() }
        } ?: emptyList()
    }

    override suspend fun load(url: String): LoadResponse? {
        return safeApiCall {
            val doc = app.get(url).document
            val title = doc.selectFirst("h1.film-title, h1.title")?.text() ?: return@safeApiCall null
            val description = doc.selectFirst("div.film-about p, .description")?.text()
            val poster = fixUrl(doc.selectFirst("div.film-poster img, .poster img")?.attr("src"))
            val year = doc.selectFirst("span.film-year, span.year")?.text()?.toIntOrNull()
            val rating = doc.selectFirst("span.imdb-rating")?.text()?.replace("[^\\d.,]".toRegex(), "")?.toRatingInt()
            val hasEpisodes = doc.select("div.episode-list a, ul.episode_list a").isNotEmpty()
            if (!hasEpisodes) {
                newMovieLoadResponse(title, url, TvType.Movie) { this.posterUrl = poster; this.plot = description; this.year = year; this.rating = rating }
            } else {
                val episodes = doc.select("div.episode-list a, ul.episode_list a").mapNotNull { ep ->
                    val epUrl = ep.attr("href")
                    val epName = ep.text().ifBlank { "Bölüm" }
                    newEpisode(epUrl) { this.name = epName; this.posterUrl = poster }
                }
                newTvSeriesLoadResponse(title, url, TvType.TvSeries, episodes) { this.posterUrl = poster; this.plot = description; this.year = year; this.rating = rating }
            }
        }
    }

    override suspend fun loadLinks(data: String, isCasting: Boolean, subtitleCallback: (SubtitleFile) -> Unit, callback: (ExtractorLink) -> Unit): Boolean {
        return safeApiCall {
            val doc = app.get(data).document
            doc.select("iframe[src]").forEach { iframe -> val src = iframe.attr("src"); if (src.isNotBlank()) loadExtractor(src, mainUrl, subtitleCallback, callback) }
            doc.select("script:containsData(video)").forEach { script ->
                val matches = Regex("(https?:\\/\\/[^\\s\"']+\\.(?:mp4|m3u8)[^\\s\"']*)").findAll(script.data())
                matches.forEach { callback(ExtractorLink(name, "Direct", it.value, mainUrl, Qualities.Unknown.value)) }
            }
            true
        } ?: false
    }

    private fun Element.toSearchResult(): SearchResponse? {
        val title = selectFirst("img")?.attr("alt") ?: selectFirst("h3, h4")?.text() ?: return null
        val href = selectFirst("a")?.attr("href") ?: return null
        val poster = fixUrl(selectFirst("img")?.attr("src"))
        val year = selectFirst("span.year")?.text()?.toIntOrNull()
        val isSeries = href.contains("/dizi/") || selectFirst("span.type")?.text()?.contains("dizi", true) == true
        return if (isSeries) newTvSeriesSearchResponse(title, fixUrl(href)!!) { this.posterUrl = poster; this.year = year } 
        else newMovieSearchResponse(title, fixUrl(href)!!) { this.posterUrl = poster; this.year = year }
    }

    private fun fixUrl(url: String?): String? {
        if (url == null) return null
        return when {
            url.startsWith("//") -> "https:$url"
            url.startsWith("/") -> mainUrl.trimEnd('/') + url
            !url.startsWith("http") -> mainUrl.trimEnd('/') + "/" + url
            else -> url
        }
    }

    private fun String?.toRatingInt(): Int? {
        return this?.replace(",", ".")?.toFloatOrNull()?.times(10)?.toInt()
    }
}
